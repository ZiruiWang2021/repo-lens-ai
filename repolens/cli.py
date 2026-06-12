from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from repolens import db
from repolens.agent import RepoLensAgent
from repolens.config import Settings
from repolens.indexer import RepositoryIndexer
from repolens.mcp_server import run_stdio_server
from repolens.providers import provider_from_settings

try:
    import typer
except ImportError:  # pragma: no cover
    typer = None  # type: ignore[assignment]


def main() -> None:
    if typer is None:
        argparse_main()
        return
    typer_main()


def typer_main() -> None:  # pragma: no cover - covered by argparse-compatible functions
    app = typer.Typer(help="RepoLens AI: cited repository Q&A, diff review, and MCP tools.")

    @app.command("index")
    def index_command(source: str) -> None:
        print_json(index_source(source))

    @app.command("ask")
    def ask_command(question: str, repo_id: int | None = None, limit: int = 6) -> None:
        print_json(ask_question(question, repo_id, limit))

    @app.command("review")
    def review_command(diff: Path = typer.Option(..., "--diff", "-d", help="Unified diff file")) -> None:
        print_json(review_diff(diff.read_text(encoding="utf-8")))

    @app.command("serve")
    def serve_command(host: str = "127.0.0.1", port: int = 8000) -> None:
        import uvicorn

        uvicorn.run("repolens.api:app", host=host, port=port, reload=False)

    @app.command("mcp")
    def mcp_command() -> None:
        run_stdio_server(Settings.from_env().db_path)

    app()


def argparse_main() -> None:
    parser = argparse.ArgumentParser(prog="repolens")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("source")

    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--repo-id", type=int, default=None)
    ask_parser.add_argument("--limit", type=int, default=6)

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("--diff", required=True)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("mcp")

    args = parser.parse_args()
    if args.command == "index":
        print_json(index_source(args.source))
    elif args.command == "ask":
        print_json(ask_question(args.question, args.repo_id, args.limit))
    elif args.command == "review":
        print_json(review_diff(Path(args.diff).read_text(encoding="utf-8")))
    elif args.command == "serve":
        raise SystemExit("Install project dependencies to use the FastAPI server: pip install -e .")
    elif args.command == "mcp":
        run_stdio_server(Settings.from_env().db_path)


def index_source(source: str) -> dict[str, Any]:
    settings = Settings.from_env()
    summary = RepositoryIndexer(settings.db_path).index(source)
    return summary.__dict__


def ask_question(question: str, repo_id: int | None = None, limit: int = 6) -> dict[str, Any]:
    settings = Settings.from_env()
    connection = db.connect(settings.db_path)
    try:
        agent = RepoLensAgent(connection, provider_from_settings(settings))
        return agent.ask(question, repo_id, limit).to_dict()
    finally:
        connection.close()


def review_diff(diff_text: str) -> dict[str, Any]:
    settings = Settings.from_env()
    connection = db.connect(settings.db_path)
    try:
        agent = RepoLensAgent(connection, provider_from_settings(settings))
        return agent.review_diff(diff_text).to_dict()
    finally:
        connection.close()


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
