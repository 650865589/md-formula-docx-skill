from pathlib import Path

from docx import Document

from scripts.equation_renderer import EquationRenderer


def _write_test_xsl(path: Path) -> None:
    xsl = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
  <xsl:output method="xml" omit-xml-declaration="yes"/>
  <xsl:template match="/">
    <m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
      <m:r><m:t><xsl:value-of select="string(.)"/></m:t></m:r>
    </m:oMath>
  </xsl:template>
</xsl:stylesheet>
"""
    path.write_text(xsl, encoding="utf-8")


def test_equation_renderer_render_inline(tmp_path: Path):
    xsl_path = tmp_path / "mml2omml.xsl"
    _write_test_xsl(xsl_path)
    renderer = EquationRenderer(str(xsl_path))

    doc = Document()
    paragraph = doc.add_paragraph("公式: ")
    renderer.render_inline(paragraph, "x^2 + y^2 = z^2")

    xml = paragraph._p.xml
    assert "m:oMath" in xml
