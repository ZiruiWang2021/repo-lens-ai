# Building RepoLens AI: A Codebase Agent That Answers With Evidence

GitHub: https://github.com/ZiruiWang2021/repo-lens-ai

Languages: [English](TECHNICAL_BLOG.md) | [简体中文](TECHNICAL_BLOG.zh-CN.md)

## Problem

Large codebases are hard to understand quickly. A new engineer often needs to answer questions like:

- Where is this behavior implemented?
- Which files are relevant to this bug?
- Does this pull request introduce a security risk?
- Can I trust the answer enough to act on it?

Most AI coding demos only show a chat interface. In real engineering work, the harder problem is context: indexing the right files, retrieving the right snippets, grounding answers in citations, and preventing repository text from controlling the agent.

## Why It Matters

For AI engineering roles, a useful codebase assistant needs more than an LLM call. It needs system design choices that make outputs reproducible, inspectable, and safe enough for developer workflows.

RepoLens AI was built to demonstrate those skills in a compact open-source project:

- Context engineering for repository-scale source files
- Retrieval-augmented generation with file citations
- Tool interfaces through CLI, REST, and MCP
- Offline demo mode so the project works without paid API keys
- Tests and CI that validate behavior beyond a happy-path demo

## My Approach

I designed RepoLens AI around one principle: repository content is useful context, but it is untrusted data.

The system first indexes a local path or public GitHub repository archive. It stores files, symbols, chunks, line ranges, summaries, and deterministic local embeddings in SQLite. When a user asks a question, the retriever combines lexical matching, vector similarity, path hints, and symbol hints to rank relevant code chunks. The agent then answers using only retrieved context and returns explicit file citations.

For pull request review, the MVP uses deterministic heuristics for risks that should be testable: hard-coded secrets, dynamic code execution, missing tests, and prompt-injection-like content. The output is a structured schema instead of free-form prose, which makes it easier to build automation on top.

## Technical Implementation

RepoLens AI uses Python 3.12 with a deliberately small stack:

- FastAPI for the local API
- Typer for the CLI
- SQLite for the local code index
- Static HTML/CSS/JavaScript for the workbench UI
- Pydantic models for stable request and response schemas
- Ruff, mypy, pytest, and GitHub Actions for engineering quality

The repository is split into focused modules:

- `repolens/indexer.py`: file filtering, chunking, symbol extraction, and repository ingestion
- `repolens/retrieval.py`: hybrid scoring across text, symbols, paths, and vectors
- `repolens/agent.py`: cited Q&A, review orchestration, and prompt-injection notes
- `repolens/providers.py`: demo, OpenAI-compatible, and Ollama provider adapters
- `repolens/api.py`: REST endpoints and static UI serving
- `repolens/mcp_server.py`: MCP tools for coding assistants

The architecture is intentionally simple enough to run locally, but each boundary maps to a production agent concern: ingestion, storage, retrieval, model adaptation, tool exposure, and evaluation.

## Results / Demo

The default demo provider requires no API key.

```bash
python -m pip install -e ".[dev]"
repolens index examples/sample_repo
repolens ask "How is the invoice total calculated?"
repolens review --diff examples/sample.diff
repolens serve
```

Example cited answer:

```json
{
  "answer": "The most relevant context for 'How is the invoice total calculated?' is app.py:13-18#calculate_total score=0.564.",
  "citations": [
    {
      "path": "app.py",
      "start_line": 13,
      "end_line": 18,
      "symbol": "calculate_total"
    }
  ],
  "uncertain": false
}
```

Example diff review:

```json
{
  "summary": "Found 3 actionable finding(s). Overall risk is high.",
  "risk_level": "high",
  "findings": [
    {
      "severity": "high",
      "category": "secret",
      "title": "Possible hard-coded secret",
      "path": "app.py"
    },
    {
      "severity": "high",
      "category": "security",
      "title": "Dynamic code execution introduced",
      "path": "app.py"
    }
  ]
}
```

The web workbench provides a small UI for indexing, asking questions, and reviewing diffs:

![RepoLens AI workbench](assets/repolens-workbench.svg)

## Limitations

This is a resume-grade MVP, not a hosted multi-tenant product.

- Embeddings use deterministic local hashing for reproducibility, not a production embedding model.
- Python symbol extraction uses the standard `ast` module; richer multi-language parsing would use tree-sitter.
- GitHub support downloads public repository archives instead of acting as a full GitHub App.
- The PR reviewer focuses on high-signal deterministic findings before delegating nuanced reasoning to an LLM.
- The UI is a static local workbench rather than a collaborative web application.

## What I Learned

The core lesson is that useful AI agents are mostly software engineering. The LLM is only one component. The surrounding system determines whether answers are grounded, inspectable, reproducible, and safe to use.

I also learned that good AI projects for hiring should be legible at two levels:

RepoLens AI was built with both audiences in mind.

## GitHub Link

https://github.com/ZiruiWang2021/repo-lens-ai
