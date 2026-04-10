from scripts.md_parser import MarkdownParser


def test_md_parser_heading_list_and_inline_code():
    parser = MarkdownParser()
    text = """# 一级标题

正文包含公式 `x^2 + y^2 = z^2` 和代码 `print(x)`.

- 列表项一 `a/b`
- 列表项二
"""
    blocks = parser.parse(text)
    assert blocks[0].kind == "heading"
    assert blocks[0].level == 1
    assert any(seg.kind == "code" and "x^2" in seg.text for seg in blocks[1].segments)
    assert blocks[2].kind == "list_item"
    assert blocks[2].ordered is False
