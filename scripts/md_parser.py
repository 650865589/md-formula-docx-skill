from __future__ import annotations

from markdown_it import MarkdownIt

from scripts.types import Block, Segment


class MarkdownParser:
    def __init__(self) -> None:
        self._md = MarkdownIt("commonmark")

    def parse(self, markdown_text: str) -> list[Block]:
        tokens = self._md.parse(markdown_text)
        blocks: list[Block] = []
        list_stack: list[bool] = []
        in_list_item = False
        index = 0

        while index < len(tokens):
            token = tokens[index]

            if token.type == "bullet_list_open":
                list_stack.append(False)
            elif token.type == "ordered_list_open":
                list_stack.append(True)
            elif token.type in {"bullet_list_close", "ordered_list_close"} and list_stack:
                list_stack.pop()
            elif token.type == "list_item_open":
                in_list_item = True
            elif token.type == "list_item_close":
                in_list_item = False
            elif token.type == "heading_open":
                level = int(token.tag[1]) if len(token.tag) == 2 else 1
                inline_token = tokens[index + 1] if index + 1 < len(tokens) else None
                segments = self._parse_inline(inline_token)
                line = (token.map[0] + 1) if token.map else 0
                blocks.append(
                    Block(
                        kind="heading",
                        level=level,
                        segments=segments,
                        line=line,
                    )
                )
            elif token.type == "paragraph_open":
                inline_token = tokens[index + 1] if index + 1 < len(tokens) else None
                segments = self._parse_inline(inline_token)
                line = (token.map[0] + 1) if token.map else 0
                if in_list_item and list_stack:
                    blocks.append(
                        Block(
                            kind="list_item",
                            ordered=list_stack[-1],
                            list_depth=max(1, len(list_stack)),
                            segments=segments,
                            line=line,
                        )
                    )
                else:
                    blocks.append(Block(kind="paragraph", segments=segments, line=line))

            index += 1

        return blocks

    def _parse_inline(self, inline_token) -> list[Segment]:
        if inline_token is None or inline_token.type != "inline":
            return []

        line = (inline_token.map[0] + 1) if inline_token.map else 0
        segments: list[Segment] = []
        for child in inline_token.children or []:
            if child.type == "code_inline":
                segments.append(Segment(kind="code", text=child.content, line=line))
            elif child.type in {"softbreak", "hardbreak"}:
                segments.append(Segment(kind="text", text="\n", line=line))
            else:
                segments.append(Segment(kind="text", text=child.content, line=line))
        return segments
