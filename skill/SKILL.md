---
name: md-formula-to-docx
description: Convert markdown plus a reference DOCX template into a DOCX file with editable Word/WPS formulas (OMML). Trigger when user asks to keep markdown text unchanged while converting inline natural formulas into editable equations.
---

# MD Formula To DOCX

## Use When
- User provides `md` content and a template `docx`.
- User wants formula expressions from inline backticks converted to editable Word/WPS equations.
- User wants formatting to follow the reference document (font, heading, line and paragraph spacing).

## Inputs
- Markdown file path.
- Template DOCX path.
- Output DOCX path.
- Optional config YAML path with LLM and XSL settings.

## Command
```powershell
py -3.10 scripts/pipeline.py --input-md <input.md> --template-docx <template.docx> --output-docx <out.docx> --config config/model.yaml --log report.json
```

## Behavior
- Parses heading/list structure from markdown.
- Keeps non-formula text unchanged.
- Detects whether inline backtick content looks like math.
- Uses LLM only for `expression -> latex`.
- Converts LaTeX to OMML and inserts editable equations.
- If one formula fails, writes `[公式转换失败]` and continues.
