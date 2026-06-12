from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "demo"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model: str = "local-hash-v1"
    db_path: Path = Path(".repolens/repolens.sqlite3")

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "demo").strip().lower(),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "local-hash-v1"),
            db_path=Path(os.getenv("REPOLENS_DB_PATH", ".repolens/repolens.sqlite3")),
        )
