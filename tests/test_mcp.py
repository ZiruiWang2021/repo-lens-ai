from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repolens.indexer import RepositoryIndexer
from repolens.mcp_server import handle_request


class McpTests(unittest.TestCase):
    def test_tools_list_and_search_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "index.sqlite3"
            RepositoryIndexer(db_path).index("examples/sample_repo")
            listed = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, db_path)
            self.assertEqual(listed["result"]["tools"][0]["name"], "search_repo")
            called = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "search_repo",
                        "arguments": {"query": "calculate_total", "limit": 2},
                    },
                },
                db_path,
            )
            text = called["result"]["content"][0]["text"]
            self.assertIn("calculate_total", text)


if __name__ == "__main__":
    unittest.main()
