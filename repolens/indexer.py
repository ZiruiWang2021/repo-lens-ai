from __future__ import annotations

import ast
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from repolens import db
from repolens.embedding import HashEmbedding
from repolens.models import CodeChunk

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".repolens",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}

EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".md": "markdown",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "powershell",
    ".html": "html",
    ".css": "css",
}


@dataclass(frozen=True)
class IndexSummary:
    repo_id: int
    repo_name: str
    root_path: str
    files_indexed: int
    chunks_indexed: int


@dataclass(frozen=True)
class SymbolRange:
    name: str
    start_line: int
    end_line: int


class RepositoryIndexer:
    def __init__(
        self,
        db_path: Path | str = ".repolens/repolens.sqlite3",
        embedding: HashEmbedding | None = None,
        max_file_bytes: int = 250_000,
        max_chunk_lines: int = 80,
        overlap_lines: int = 10,
    ) -> None:
        self.db_path = Path(db_path)
        self.embedding = embedding or HashEmbedding()
        self.max_file_bytes = max_file_bytes
        self.max_chunk_lines = max_chunk_lines
        self.overlap_lines = overlap_lines

    def index(self, source: str | Path) -> IndexSummary:
        materialized = materialize_source(source)
        root = materialized.path.resolve()
        connection = db.connect(self.db_path)
        try:
            repo_id = db.upsert_repo(connection, str(root), root.name)
            chunks: list[CodeChunk] = []
            files_indexed = 0
            for path in iter_source_files(root, self.max_file_bytes):
                text = path.read_text(encoding="utf-8", errors="replace")
                language = detect_language(path)
                relative_path = path.relative_to(root).as_posix()
                file_chunks = self.chunk_file(
                    repo_id=repo_id,
                    relative_path=relative_path,
                    language=language,
                    text=text,
                )
                chunks.extend(file_chunks)
                files_indexed += 1
            db.insert_chunks(connection, chunks)
            connection.commit()
            return IndexSummary(
                repo_id=repo_id,
                repo_name=root.name,
                root_path=str(root),
                files_indexed=files_indexed,
                chunks_indexed=len(chunks),
            )
        finally:
            connection.close()
            materialized.cleanup()

    def chunk_file(
        self,
        repo_id: int,
        relative_path: str,
        language: str,
        text: str,
    ) -> list[CodeChunk]:
        lines = text.splitlines()
        if not lines:
            return []

        symbol_ranges = extract_python_symbols(text) if language == "python" else []
        chunks: list[CodeChunk] = []
        covered: set[tuple[int, int]] = set()

        for symbol in symbol_ranges:
            if symbol.end_line - symbol.start_line + 1 <= self.max_chunk_lines * 2:
                content = slice_lines(lines, symbol.start_line, symbol.end_line)
                chunks.append(
                    self._make_chunk(
                        repo_id,
                        relative_path,
                        language,
                        symbol.name,
                        symbol.start_line,
                        symbol.end_line,
                        content,
                    )
                )
                covered.add((symbol.start_line, symbol.end_line))

        step = max(1, self.max_chunk_lines - self.overlap_lines)
        for start in range(1, len(lines) + 1, step):
            end = min(len(lines), start + self.max_chunk_lines - 1)
            if any(start >= covered_start and end <= covered_end for covered_start, covered_end in covered):
                continue
            content = slice_lines(lines, start, end)
            symbol_name = symbol_for_range(symbol_ranges, start, end)
            chunks.append(
                self._make_chunk(
                    repo_id,
                    relative_path,
                    language,
                    symbol_name,
                    start,
                    end,
                    content,
                )
            )

        return deduplicate_chunks(chunks)

    def _make_chunk(
        self,
        repo_id: int,
        path: str,
        language: str,
        symbol: str | None,
        start_line: int,
        end_line: int,
        content: str,
    ) -> CodeChunk:
        summary = summarize_chunk(path, symbol, content)
        embedding_text = f"{path}\n{symbol or ''}\n{summary}\n{content}"
        return CodeChunk(
            id=None,
            repo_id=repo_id,
            path=path,
            language=language,
            symbol=symbol,
            start_line=start_line,
            end_line=end_line,
            content=content,
            summary=summary,
            embedding=self.embedding.embed(embedding_text),
        )


class MaterializedSource:
    def __init__(self, path: Path, temp_dir: tempfile.TemporaryDirectory[str] | None = None) -> None:
        self.path = path
        self._temp_dir = temp_dir

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()


def materialize_source(source: str | Path) -> MaterializedSource:
    source_text = str(source)
    local = Path(source_text)
    if local.exists():
        if not local.is_dir():
            raise ValueError(f"source must be a directory: {source_text}")
        return MaterializedSource(local)

    parsed = urllib.parse.urlparse(source_text)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError(f"source is not a local directory or GitHub URL: {source_text}")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must include owner and repository")

    owner, repo = parts[0], parts[1].removesuffix(".git")
    branch = parts[3] if len(parts) >= 4 and parts[2] in {"tree", "blob"} else "main"
    archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    temp_dir = tempfile.TemporaryDirectory(prefix="repolens-github-")
    archive_path = Path(temp_dir.name) / "repo.zip"
    urllib.request.urlretrieve(archive_url, archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(temp_dir.name)
    extracted = [path for path in Path(temp_dir.name).iterdir() if path.is_dir()]
    if not extracted:
        temp_dir.cleanup()
        raise ValueError("downloaded GitHub archive did not contain a directory")
    return MaterializedSource(extracted[0], temp_dir)


def iter_source_files(root: Path, max_file_bytes: int) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if detect_language(path) == "text":
            continue
        if path.stat().st_size > max_file_bytes:
            continue
        if is_binary(path):
            continue
        files.append(path)
    return sorted(files)


def detect_language(path: Path) -> str:
    return EXTENSIONS.get(path.suffix.lower(), "text")


def is_binary(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\x00" in sample


def extract_python_symbols(text: str) -> list[SymbolRange]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    symbols: list[SymbolRange] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end_line = getattr(node, "end_lineno", node.lineno)
            symbols.append(SymbolRange(node.name, node.lineno, end_line))
    return sorted(symbols, key=lambda symbol: (symbol.start_line, symbol.end_line))


def symbol_for_range(symbols: list[SymbolRange], start_line: int, end_line: int) -> str | None:
    midpoint = (start_line + end_line) // 2
    for symbol in symbols:
        if symbol.start_line <= midpoint <= symbol.end_line:
            return symbol.name
    return None


def slice_lines(lines: list[str], start_line: int, end_line: int) -> str:
    return "\n".join(lines[start_line - 1 : end_line])


def summarize_chunk(path: str, symbol: str | None, content: str) -> str:
    meaningful = [line.strip() for line in content.splitlines() if line.strip()]
    preview = " ".join(meaningful[:3])
    if len(preview) > 220:
        preview = preview[:217] + "..."
    subject = f"{path}::{symbol}" if symbol else path
    return f"{subject} - {preview}" if preview else subject


def deduplicate_chunks(chunks: list[CodeChunk]) -> list[CodeChunk]:
    seen: set[tuple[str, int, int, str | None]] = set()
    unique: list[CodeChunk] = []
    for chunk in chunks:
        key = (chunk.path, chunk.start_line, chunk.end_line, chunk.symbol)
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique
