from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repolens import db
from repolens.agent import RepoLensAgent
from repolens.indexer import RepositoryIndexer


class AgentTests(unittest.TestCase):
    def test_cited_answer_and_prompt_injection_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "index.sqlite3"
            summary = RepositoryIndexer(db_path).index("examples/sample_repo")
            connection = db.connect(db_path)
            try:
                answer = RepoLensAgent(connection).ask("Where is prompt injection mentioned?", summary.repo_id)
            finally:
                connection.close()
            self.assertFalse(answer.uncertain)
            self.assertIn("[1]", answer.answer)
            self.assertTrue(answer.security_notes)

    def test_review_flags_security_and_missing_tests(self) -> None:
        diff = Path("examples/sample.diff").read_text(encoding="utf-8")
        connection = db.connect(Path(tempfile.mkdtemp()) / "index.sqlite3")
        try:
            report = RepoLensAgent(connection).review_diff(diff)
        finally:
            connection.close()
        categories = {finding.category for finding in report.findings}
        self.assertIn("security", categories)
        self.assertIn("secret", categories)
        self.assertIn("testing", categories)
        self.assertEqual(report.risk_level, "high")


if __name__ == "__main__":
    unittest.main()
