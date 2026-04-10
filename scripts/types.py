from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Segment:
    kind: str
    text: str
    line: int = 0
    column: int = 1


@dataclass
class Block:
    kind: str
    segments: list[Segment] = field(default_factory=list)
    level: int = 0
    ordered: bool = False
    list_depth: int = 0
    line: int = 0


@dataclass
class FormulaFailure:
    expression: str
    line: int
    stage: str
    error: str


@dataclass
class RenderReport:
    input_md: str
    template_docx: str
    output_docx: str
    total_formula_candidates: int = 0
    formula_success: int = 0
    formula_failed: int = 0
    failures: list[FormulaFailure] = field(default_factory=list)
    style_map: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_md": self.input_md,
            "template_docx": self.template_docx,
            "output_docx": self.output_docx,
            "total_formula_candidates": self.total_formula_candidates,
            "formula_success": self.formula_success,
            "formula_failed": self.formula_failed,
            "failures": [
                {
                    "expression": item.expression,
                    "line": item.line,
                    "stage": item.stage,
                    "error": item.error,
                }
                for item in self.failures
            ],
            "style_map": self.style_map,
        }
