from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

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
    batch_size: int = 12
    wire_api: str = "chat_completions"


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

    def normalize_many(self, expressions: list[str]) -> tuple[dict[str, str], dict[str, str]]:
        if not expressions:
            return {}, {}

        results: dict[str, str] = {}
        errors: dict[str, str] = {}
        for index in range(0, len(expressions), self._config.batch_size):
            batch = expressions[index : index + self._config.batch_size]
            try:
                batch_results = self._request_batch(batch)
                for expr in batch:
                    latex = batch_results.get(expr, "").strip()
                    if latex:
                        results[expr] = latex
                    else:
                        errors[expr] = "batch response missing latex"
            except Exception as exc:  # noqa: BLE001
                # Fallback to single-item calls to reduce overall failure impact.
                for expr in batch:
                    try:
                        results[expr] = self.to_latex(expr)
                    except Exception as single_exc:  # noqa: BLE001
                        errors[expr] = str(single_exc if single_exc else exc)
        return results, errors

    def _request_once(self, expression: str) -> str:
        if self._config.wire_api == "responses":
            message = self._request_responses_text(
                (
                    "You normalize natural-language math expressions into valid LaTeX. "
                    "Respond with strict JSON only: "
                    '{"latex":"<latex here>"}\n'
                    f"Expression: {expression}"
                )
            )
        else:
            url = _build_chat_url(self._config.base_url)
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
            data = _parse_json_response(response)
            message = _extract_assistant_text(data)
            if not message:
                raise LatexNormalizeError(f"No assistant content in response: {_safe_preview(data)}")
        latex = _extract_latex(message)
        if not latex.strip():
            raise LatexNormalizeError("LLM returned empty latex")
        return latex.strip()

    def _request_batch(self, expressions: list[str]) -> dict[str, str]:
        indexed = [{"id": i, "expression": expr} for i, expr in enumerate(expressions)]
        if self._config.wire_api == "responses":
            prompt = (
                "Convert each expression into valid LaTeX. "
                "Return strict JSON only in this shape: "
                '{"items":[{"id":0,"latex":"..."}]}\n'
                f'{json.dumps({"items": indexed}, ensure_ascii=False)}'
            )
            text = self._request_responses_text(prompt)
        else:
            url = _build_chat_url(self._config.base_url)
            payload = {
                "model": self._config.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Convert each expression into valid LaTeX. "
                            "Return strict JSON only in this shape: "
                            '{"items":[{"id":0,"latex":"..."}]}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({"items": indexed}, ensure_ascii=False),
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
            data = _parse_json_response(response)
            text = _extract_assistant_text(data)
            if not text:
                raise LatexNormalizeError(f"No assistant content in batch response: {_safe_preview(data)}")

        parsed = _extract_json_payload(text)
        items = parsed.get("items", []) if isinstance(parsed, dict) else []
        result: dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            latex = str(item.get("latex", "")).strip()
            if isinstance(item_id, int) and 0 <= item_id < len(expressions) and latex:
                result[expressions[item_id]] = latex
        return result

    def _request_responses_text(self, prompt: str) -> str:
        url = _build_responses_url(self._config.base_url)
        payload = {
            "model": self._config.model,
            "input": prompt,
            "stream": True,
        }
        response = self._session.post(
            url,
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._config.timeout,
            stream=True,
        )
        response.raise_for_status()
        text = _extract_text_from_responses_sse(response)
        if not text.strip():
            raise LatexNormalizeError("Empty text from responses stream")
        return text


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


def _build_chat_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _build_responses_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/responses"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/responses"
    return f"{normalized}/responses"


def _parse_json_response(response: requests.Response) -> dict[str, Any]:
    text = response.text.strip()
    if not text:
        raise LatexNormalizeError("Empty API response body")

    # Some gateways return text/event-stream but body is a single JSON object.
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        pass

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise LatexNormalizeError(f"Could not parse JSON response: {text[:300]}")


def _extract_assistant_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message", {})
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, dict):
                        txt = part.get("text")
                        if isinstance(txt, str) and txt:
                            parts.append(txt)
                if parts:
                    return "".join(parts)
        text = choice.get("text")
        if isinstance(text, str) and text.strip():
            return text
        delta = choice.get("delta", {})
        if isinstance(delta, dict):
            delta_text = delta.get("content")
            if isinstance(delta_text, str) and delta_text.strip():
                return delta_text

    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = data.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict):
                    txt = content.get("text")
                    if isinstance(txt, str) and txt:
                        parts.append(txt)
        if parts:
            return "".join(parts)
    return ""


def _extract_json_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    code_block = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    raise LatexNormalizeError("Could not parse JSON payload from model response")


def _extract_text_from_responses_sse(response: requests.Response) -> str:
    deltas: list[str] = []
    final_text: str | None = None

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")
        if event_type == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                deltas.append(delta)
        elif event_type == "response.output_text.done":
            text = event.get("text")
            if isinstance(text, str):
                final_text = text
        elif event_type == "response.completed":
            # Keep reading already collected deltas/text; this event may still have empty output.
            pass

    if final_text and final_text.strip():
        return final_text
    return "".join(deltas)


def _safe_preview(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)[:300]
    except Exception:  # noqa: BLE001
        return str(data)[:300]
