from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repolens import db
from repolens.indexer import RepositoryIndexer, extract_python_symbols


class IndexerTests(unittest.TestCase):
    def test_extract_python_symbols(self) -> None:
        symbols = extract_python_symbols("class A:\n    pass\n\ndef f():\n    return 1\n")
        self.assertEqual([symbol.name for symbol in symbols], ["A", "f"])

    def test_indexes_sample_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "index.sqlite3"
            summary = RepositoryIndexer(db_path).index("examples/sample_repo")
            self.assertGreaterEqual(summary.files_indexed, 2)
            self.assertGreaterEqual(summary.chunks_indexed, 2)
            connection = db.connect(db_path)
            try:
                repo = db.repo_map(connection, summary.repo_id)
            finally:
                connection.close()
            self.assertIn("app.py", {item["path"] for item in repo["files"]})


if __name__ == "__main__":
    unittest.main()
