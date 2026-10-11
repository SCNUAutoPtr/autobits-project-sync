"""Public workflow failures must not expose private GitHub API responses."""
import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class PublicLogRedactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = runpy.run_path(
            str(Path(__file__).resolve().parents[1] / "scripts/global-project-sync.py"),
            run_name="privacy_test",
        )

    def assert_failure_is_redacted(self, response):
        gql = self.module["gql"]
        with patch.object(gql.__globals__["subprocess"], "run", return_value=response):
            with self.assertRaises(RuntimeError) as raised:
                gql("query { viewer { login } }")
        self.assertNotIn("PRIVATE_ISSUE_CANARY", str(raised.exception))

    def test_http_failure_redacts_stdout_and_stderr(self):
        self.assert_failure_is_redacted(SimpleNamespace(
            returncode=1,
            stdout="PRIVATE_ISSUE_CANARY in partial data",
            stderr="PRIVATE_ISSUE_CANARY in error details",
        ))

    def test_graphql_partial_success_redacts_errors_and_private_data(self):
        self.assert_failure_is_redacted(SimpleNamespace(
            returncode=0,
            stdout=json.dumps({
                "errors": [{"message": "PRIVATE_ISSUE_CANARY"}],
                "data": {"title": "PRIVATE_ISSUE_CANARY"},
            }),
            stderr="",
        ))


if __name__ == "__main__":
    unittest.main()
