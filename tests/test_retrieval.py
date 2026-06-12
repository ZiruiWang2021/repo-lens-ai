from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repolens import db
from repolens.indexer import RepositoryIndexer
from repolens.retrieval import HybridRetriever


class RetrievalTests(unittest.TestCase):
    def test_symbol_and_keyword_boost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "index.sqlite3"
            summary = RepositoryIndexer(db_path).index("examples/sample_repo")
            connection = db.connect(db_path)
            try:
                results = HybridRetriever(connection).search("calculate_total coupon", summary.repo_id)
            finally:
                connection.close()
            self.assertTrue(results)
            self.assertEqual(results[0].chunk.path, "app.py")
            self.assertIn("calculate_total", results[0].chunk.content)


if __name__ == "__main__":
    unittest.main()
