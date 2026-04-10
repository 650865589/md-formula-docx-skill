from __future__ import annotations

from docx import Document


def load_template_document(template_path: str):
    return Document(template_path)


def clear_document_content(document) -> None:
    body = document._body._element
    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)
