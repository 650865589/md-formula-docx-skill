from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from docx.oxml import parse_xml
from latex2mathml.converter import convert as latex_to_mathml
from lxml import etree


class EquationRenderError(RuntimeError):
    pass


class EquationRenderer:
    def __init__(self, mml2omml_xsl_path: str) -> None:
        xsl_path = Path(mml2omml_xsl_path)
        if not xsl_path.exists():
            raise EquationRenderError(f"MML2OMML XSL not found: {xsl_path}")
        xsl_doc = etree.parse(str(xsl_path))
        self._transform = etree.XSLT(xsl_doc)

    def latex_to_omml(self, latex: str):
        try:
            mathml = latex_to_mathml(latex)
            return self.mathml_to_omml(mathml)
        except Exception as exc:  # noqa: BLE001
            raise EquationRenderError(f"Failed to convert latex to OMML: {exc}") from exc

    def mathml_to_omml(self, mathml: str):
        try:
            mathml_root = etree.fromstring(mathml.encode("utf-8"))
            transformed = self._transform(mathml_root)
            xml = etree.tostring(
                transformed.getroot(), encoding="unicode", xml_declaration=False
            )
            return parse_xml(xml)
        except Exception as exc:  # noqa: BLE001
            raise EquationRenderError(f"Failed to transform MathML to OMML: {exc}") from exc

    def render_inline(self, paragraph, latex: str) -> None:
        omml = self.latex_to_omml(latex)
        run = paragraph.add_run()
        run._r.append(deepcopy(omml))
