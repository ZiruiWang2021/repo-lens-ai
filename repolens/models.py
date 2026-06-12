from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    path: str
    start_line: int
    end_line: int
    symbol: str | None = None

    def label(self) -> str:
        suffix = f"#{self.symbol}" if self.symbol else ""
        return f"{self.path}:{self.start_line}-{self.end_line}{suffix}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CodeChunk:
    id: int | None
    repo_id: int
    path: str
    language: str
    symbol: str | None
    start_line: int
    end_line: int
    content: str
    summary: str
    embedding: list[float] = field(default_factory=list)

    @property
    def citation(self) -> Citation:
        return Citation(
            path=self.path,
            start_line=self.start_line,
            end_line=self.end_line,
            symbol=self.symbol,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["citation"] = self.citation.to_dict()
        return data


@dataclass(frozen=True)
class SearchResult:
    chunk: CodeChunk
    score: float
    keyword_score: float
    vector_score: float
    path_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "keyword_score": self.keyword_score,
            "vector_score": self.vector_score,
            "path_score": self.path_score,
        }


@dataclass(frozen=True)
class ChatAnswer:
    answer: str
    citations: list[Citation]
    uncertain: bool
    security_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "uncertain": self.uncertain,
            "security_notes": self.security_notes,
        }


@dataclass(frozen=True)
class ReviewFinding:
    severity: str
    category: str
    title: str
    detail: str
    path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewReport:
    summary: str
    findings: list[ReviewFinding]
    suggested_tests: list[str]
    risk_level: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "findings": [finding.to_dict() for finding in self.findings],
            "suggested_tests": self.suggested_tests,
            "risk_level": self.risk_level,
        }
