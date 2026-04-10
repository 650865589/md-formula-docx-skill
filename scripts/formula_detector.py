from __future__ import annotations

import re


class FormulaDetector:
    _BLACKLIST_PATTERNS = [
        r"\bdef\b",
        r"\bclass\b",
        r"\breturn\b",
        r"\bprint\s*\(",
        r"\bimport\b",
        r"=>",
        r"===",
        r"!=",
        r"&&|\|\|",
        r"{|}",
        r";",
        r"</?\w+",
        r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b",
    ]
    _FUNCTION_PATTERN = re.compile(
        r"\b(sin|cos|tan|log|ln|exp|max|min|sqrt|abs|mean|std)\b", re.IGNORECASE
    )
    _MATH_SYMBOL_PATTERN = re.compile(r"[=+\-*/^<>≤≥≈×÷∑∏√∫∞∆∂]")
    _GREEK_PATTERN = re.compile(r"[α-ωΑ-ΩπΠσΣμλθΔΩ]|\\(alpha|beta|gamma|delta|theta|pi|sigma|mu|lambda)\b")
    _FRACTION_PATTERN = re.compile(r"\d+\s*/\s*\d+")
    _IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    _DIGIT_PATTERN = re.compile(r"\d")

    def __init__(self) -> None:
        self._blacklist = [re.compile(p, re.IGNORECASE) for p in self._BLACKLIST_PATTERNS]

    def is_formula_expression(self, text: str) -> bool:
        expr = text.strip()
        if not expr:
            return False

        for pattern in self._blacklist:
            if pattern.search(expr):
                return False

        score = 0
        if self._MATH_SYMBOL_PATTERN.search(expr):
            score += 2
        if self._GREEK_PATTERN.search(expr):
            score += 2
        if self._FUNCTION_PATTERN.search(expr):
            score += 1
        if self._FRACTION_PATTERN.search(expr):
            score += 1

        has_identifier = bool(self._IDENTIFIER_PATTERN.search(expr))
        has_digit = bool(self._DIGIT_PATTERN.search(expr))
        if has_identifier and has_digit:
            score += 1

        if "=" in expr and has_identifier:
            score += 1

        # Reject obvious single-word code-like values when no math evidence exists.
        if score == 0 and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
            return False

        return score >= 2
