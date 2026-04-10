from __future__ import annotations

from docx.enum.style import WD_STYLE_TYPE


class StyleMapper:
    def __init__(self, document) -> None:
        self._document = document
        self._style_name_lookup = {
            style.name.lower(): style.name
            for style in document.styles
            if style.type in {WD_STYLE_TYPE.PARAGRAPH, WD_STYLE_TYPE.CHARACTER}
        }

    def resolve_paragraph_style(
        self, kind: str, level: int = 1, ordered: bool = False, depth: int = 1
    ) -> str | None:
        if kind == "heading":
            return self._resolve(
                [
                    f"Heading {level}",
                    f"标题 {level}",
                    f"Heading{level}",
                ]
            )

        if kind == "list_item":
            if ordered:
                return self._resolve(
                    [f"List Number {depth}", "List Number", f"编号 {depth}", "编号"]
                )
            return self._resolve(
                [f"List Bullet {depth}", "List Bullet", f"项目符号 {depth}", "项目符号"]
            )

        return self._resolve(["Normal", "正文", "Body Text"])

    def style_summary(self) -> dict[str, dict[str, str | None]]:
        summary: dict[str, dict[str, str | None]] = {}
        style_targets = {
            "paragraph": self.resolve_paragraph_style("paragraph"),
            "heading_1": self.resolve_paragraph_style("heading", level=1),
            "heading_2": self.resolve_paragraph_style("heading", level=2),
            "heading_3": self.resolve_paragraph_style("heading", level=3),
            "list_bullet": self.resolve_paragraph_style("list_item", ordered=False, depth=1),
            "list_number": self.resolve_paragraph_style("list_item", ordered=True, depth=1),
        }

        for key, style_name in style_targets.items():
            if not style_name:
                summary[key] = {"name": None, "font": None, "line_spacing": None, "space_before": None, "space_after": None}
                continue
            style = self._document.styles[style_name]
            pf = style.paragraph_format
            summary[key] = {
                "name": style_name,
                "font": style.font.name,
                "line_spacing": str(pf.line_spacing) if pf.line_spacing is not None else None,
                "space_before": str(pf.space_before) if pf.space_before is not None else None,
                "space_after": str(pf.space_after) if pf.space_after is not None else None,
            }
        return summary

    def _resolve(self, candidates: list[str]) -> str | None:
        for candidate in candidates:
            matched = self._style_name_lookup.get(candidate.lower())
            if matched:
                return matched
        return None
