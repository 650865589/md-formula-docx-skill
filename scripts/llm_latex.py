from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass

import requests


class LatexNormalizeError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout: int = 30
    max_retries: int = 2


class LatexNormalizer:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._session = requests.Session()

    def to_latex(self, expression: str) -> str:
        last_error: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                return self._request_once(expression)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self._config.max_retries:
                    time.sleep(min(2.0, 0.5 * (attempt + 1)))
        raise LatexNormalizeError(f"LLM latex normalize failed: {last_error}")

    def _request_once(self, expression: str) -> str:
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You normalize natural-language math expressions into valid LaTeX. "
                        "Respond with strict JSON only: "
                        '{"latex":"<latex here>"}'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Expression: {expression}",
                },
            ],
        }
        response = self._session.post(
            url,
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._config.timeout,
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]["content"]
        latex = _extract_latex(message)
        if not latex.strip():
            raise LatexNormalizeError("LLM returned empty latex")
        return latex.strip()


def _extract_latex(content: str) -> str:
    text = content.strip()
    try:
        data = json.loads(text)
        latex = data.get("latex", "")
        if isinstance(latex, str) and latex:
            return latex
    except json.JSONDecodeError:
        pass

    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            latex = data.get("latex", "")
            if isinstance(latex, str) and latex:
                return latex
        except json.JSONDecodeError:
            pass

    inline = re.search(r'"latex"\s*:\s*"([^"]+)"', text)
    if inline:
        return inline.group(1)

    raise LatexNormalizeError("Could not parse latex from LLM response")
