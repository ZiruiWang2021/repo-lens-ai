from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from repolens import db
from repolens.agent import RepoLensAgent
from repolens.retrieval import HybridRetriever

TOOLS = [
    {
        "name": "search_repo",
        "description": "Search indexed repository chunks with hybrid keyword and vector scoring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "repo_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 6},
            },
            "required": ["query"],
        },
    },
    {
        "name": "explain_symbol",
        "description": "Find and explain indexed chunks related to a symbol name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "repo_id": {"type": "integer"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "review_diff",
        "description": "Review a unified diff for bugs, missing tests, security, and prompt-injection risks.",
        "inputSchema": {
            "type": "object",
            "properties": {"diff": {"type": "string"}},
            "required": ["diff"],
        },
    },
]


def run_stdio_server(db_path: str | Path) -> None:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request, Path(db_path))
        except Exception as exc:  # noqa: BLE001
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def handle_request(request: dict[str, Any], db_path: Path) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "repo-lens-ai", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        result = call_tool(name, arguments, db_path)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
        }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def call_tool(name: str, arguments: dict[str, Any], db_path: Path) -> dict[str, Any]:
    connection = db.connect(db_path)
    try:
        if name == "search_repo":
            repo_id = arguments.get("repo_id")
            retriever = HybridRetriever(connection)
            results = retriever.search(
                str(arguments["query"]),
                int(repo_id) if repo_id is not None else None,
                int(arguments.get("limit", 6)),
            )
            return {"results": [result.to_dict() for result in results]}
        if name == "explain_symbol":
            symbol = str(arguments["symbol"])
            repo_id = arguments.get("repo_id")
            agent = RepoLensAgent(connection)
            return agent.ask(f"Explain symbol {symbol}", int(repo_id) if repo_id is not None else None).to_dict()
        if name == "review_diff":
            agent = RepoLensAgent(connection)
            return agent.review_diff(str(arguments["diff"])).to_dict()
        raise ValueError(f"unknown tool: {name}")
    finally:
        connection.close()
