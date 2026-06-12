from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from repolens.config import Settings


class ProviderError(RuntimeError):
    pass


class LLMProvider:
    name = "base"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    def stream(self, system_prompt: str, user_prompt: str) -> Iterable[str]:
        yield self.complete(system_prompt, user_prompt)


class DemoProvider(LLMProvider):
    name = "demo"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt
        question = extract_tag(user_prompt, "question") or "the question"
        citations = re.findall(r"\[(\d+)\]\s+([^\n]+)", user_prompt)
        if "review diff" in user_prompt.lower() or "<diff>" in user_prompt:
            return "I reviewed the diff using deterministic offline heuristics."
        if not citations:
            return "I do not have enough indexed context to answer confidently."
        cited = ", ".join(f"[{number}]" for number, _ in citations[:3])
        first_context = citations[0][1]
        return (
            f"The most relevant context for '{question}' is {first_context}. "
            f"Use the cited files to verify behavior and ownership: {cited}."
        )


@dataclass(frozen=True)
class OpenAICompatibleProvider(LLMProvider):
    base_url: str
    api_key: str
    model: str
    name: str = "openai"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is required for the OpenAI-compatible provider")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        response = post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            {"Authorization": f"Bearer {self.api_key}"},
        )
        try:
            return str(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected OpenAI-compatible response: {response}") from exc


@dataclass(frozen=True)
class OllamaProvider(LLMProvider):
    base_url: str
    model: str
    name: str = "ollama"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        response = post_json(f"{self.base_url.rstrip('/')}/api/chat", payload, {})
        try:
            return str(response["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"unexpected Ollama response: {response}") from exc


def provider_from_settings(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider or os.getenv("LLM_PROVIDER", "demo")
    if provider == "demo":
        return DemoProvider()
    if provider in {"openai", "openai-compatible", "compatible"}:
        return OpenAICompatibleProvider(
            settings.openai_base_url,
            settings.openai_api_key,
            settings.openai_model,
        )
    if provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    raise ProviderError(f"unsupported provider: {provider}")


def post_json(url: str, payload: dict[str, object], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))
    except urllib.error.URLError as exc:
        raise ProviderError(f"provider request failed: {exc}") from exc


def extract_tag(text: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL)
    return match.group(1).strip() if match else None
