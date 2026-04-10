from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from scripts.docx_writer import clear_document_content, load_template_document
from scripts.equation_renderer import EquationRenderError, EquationRenderer
from scripts.formula_detector import FormulaDetector
from scripts.llm_latex import LLMConfig, LatexNormalizer
from scripts.md_parser import MarkdownParser
from scripts.style_mapper import StyleMapper
from scripts.render_types import FormulaFailure, RenderReport


class LatexNormalizerProtocol(Protocol):
    def to_latex(self, expression: str) -> str:
        ...

    def normalize_many(self, expressions: list[str]) -> tuple[dict[str, str], dict[str, str]]:
        ...


@dataclass
class PipelineConfig:
    mml2omml_xsl: str
    failure_placeholder: str = "[公式转换失败]"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    llm_timeout: int = 30
    llm_max_retries: int = 2
    llm_batch_size: int = 12
    llm_wire_api: str = "chat_completions"


def load_config(config_path: str | None) -> PipelineConfig:
    if not config_path:
        # Office path discovered in earlier environment check.
        return PipelineConfig(
            mml2omml_xsl=r"C:\Program Files (x86)\Microsoft Office\Office14\MML2OMML.XSL"
        )

    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    llm = raw.get("llm", {})
    equation = raw.get("equation", {})
    output = raw.get("output", {})

    api_key = llm.get("api_key", "")
    api_key_env = llm.get("api_key_env", "")
    if not api_key and api_key_env:
        api_key = os.getenv(api_key_env, "")

    return PipelineConfig(
        mml2omml_xsl=equation.get(
            "mml2omml_xsl",
            r"C:\Program Files (x86)\Microsoft Office\Office14\MML2OMML.XSL",
        ),
        failure_placeholder=output.get("failure_placeholder", "[公式转换失败]"),
        llm_base_url=llm.get("base_url", "https://api.openai.com/v1"),
        llm_api_key=api_key,
        llm_model=llm.get("model", "gpt-4.1-mini"),
        llm_timeout=int(llm.get("timeout", 30)),
        llm_max_retries=int(llm.get("max_retries", 2)),
        llm_batch_size=int(llm.get("batch_size", 12)),
        llm_wire_api=llm.get("wire_api", "chat_completions"),
    )


def build_normalizer(config: PipelineConfig) -> LatexNormalizerProtocol:
    if not config.llm_api_key:
        raise ValueError("Missing llm api key; set llm.api_key or llm.api_key_env in config.")

    return LatexNormalizer(
        LLMConfig(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model=config.llm_model,
            timeout=config.llm_timeout,
            max_retries=config.llm_max_retries,
            batch_size=config.llm_batch_size,
            wire_api=config.llm_wire_api,
        )
    )


def convert_markdown_to_docx(
    input_md_path: str,
    template_docx_path: str,
    output_docx_path: str,
    config: PipelineConfig,
    log_path: str | None = None,
    normalizer: LatexNormalizerProtocol | None = None,
) -> dict:
    parser = MarkdownParser()
    detector = FormulaDetector()
    renderer = EquationRenderer(config.mml2omml_xsl)
    normalizer_impl = normalizer or build_normalizer(config)

    markdown_text = Path(input_md_path).read_text(encoding="utf-8")
    blocks = parser.parse(markdown_text)

    document = load_template_document(template_docx_path)
    clear_document_content(document)
    styles = StyleMapper(document)

    report = RenderReport(
        input_md=str(Path(input_md_path).resolve()),
        template_docx=str(Path(template_docx_path).resolve()),
        output_docx=str(Path(output_docx_path).resolve()),
        style_map=styles.style_summary(),
    )

    latex_cache: dict[str, str] = {}
    llm_errors: dict[str, str] = {}

    formula_exprs: list[str] = []
    for block in blocks:
        for segment in block.segments:
            if segment.kind == "code" and detector.is_formula_expression(segment.text):
                formula_exprs.append(segment.text)

    unique_formula_exprs = list(dict.fromkeys(formula_exprs))
    if unique_formula_exprs and hasattr(normalizer_impl, "normalize_many"):
        try:
            batch_results, batch_errors = normalizer_impl.normalize_many(unique_formula_exprs)
            latex_cache.update(batch_results)
            llm_errors.update(batch_errors)
        except Exception:
            # Fallback to per-expression path below.
            pass

    for block in blocks:
        style_name = styles.resolve_paragraph_style(
            kind=block.kind,
            level=block.level if block.level else 1,
            ordered=block.ordered,
            depth=block.list_depth if block.list_depth else 1,
        )
        paragraph = document.add_paragraph(style=style_name) if style_name else document.add_paragraph()

        for segment in block.segments:
            if segment.kind == "text":
                paragraph.add_run(segment.text)
                continue

            if segment.kind != "code":
                paragraph.add_run(segment.text)
                continue

            if not detector.is_formula_expression(segment.text):
                paragraph.add_run(f"`{segment.text}`")
                continue

            report.total_formula_candidates += 1
            try:
                latex = latex_cache.get(segment.text)
                if latex is None:
                    if segment.text in llm_errors:
                        raise RuntimeError(llm_errors[segment.text])
                    latex = normalizer_impl.to_latex(segment.text)
                    latex_cache[segment.text] = latex
            except Exception as exc:  # noqa: BLE001
                paragraph.add_run(config.failure_placeholder)
                report.formula_failed += 1
                report.failures.append(
                    FormulaFailure(
                        expression=segment.text,
                        line=segment.line,
                        stage="llm_latex",
                        error=str(exc),
                    )
                )
                continue

            try:
                renderer.render_inline(paragraph, latex)
                report.formula_success += 1
            except EquationRenderError as exc:
                paragraph.add_run(config.failure_placeholder)
                report.formula_failed += 1
                report.failures.append(
                    FormulaFailure(
                        expression=segment.text,
                        line=segment.line,
                        stage="omml_render",
                        error=str(exc),
                    )
                )

    output_path = Path(output_docx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))

    result = report.as_dict()
    if log_path:
        log_output = Path(log_path)
        log_output.parent.mkdir(parents=True, exist_ok=True)
        log_output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert markdown into styled docx with editable OMML formulas."
    )
    parser.add_argument("--input-md", required=True, help="Input markdown file path.")
    parser.add_argument("--template-docx", required=True, help="Template docx file path.")
    parser.add_argument("--output-docx", required=True, help="Output docx file path.")
    parser.add_argument("--config", required=False, help="YAML config path.")
    parser.add_argument("--log", required=False, help="JSON report path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    result = convert_markdown_to_docx(
        input_md_path=args.input_md,
        template_docx_path=args.template_docx,
        output_docx_path=args.output_docx,
        config=config,
        log_path=args.log,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
