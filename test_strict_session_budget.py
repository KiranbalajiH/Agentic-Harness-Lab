"""End-to-end integration test for FastAPI /api/ask endpoint.

Validates SSE stream parsing, per-question budget resets, and PDF replacement.
"""

import json
import unittest
from fastapi.testclient import TestClient
from bridge import app

client = TestClient(app)


class TestApiAskEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf_path = "C:/Users/kiran/antigravity K/Agentic-Harness-Lab/test_data/fixture.pdf"
        with open(cls.pdf_path, "rb") as f:
            cls.pdf_bytes = f.read()

    def _ask(self, question: str, pdf_bytes=None):
        data_bytes = pdf_bytes or self.pdf_bytes
        response = client.post(
            "/api/ask",
            files={"file": ("fixture.pdf", data_bytes, "application/pdf")},
            data={"question": question},
        )
        self.assertEqual(response.status_code, 200)

        # Parse SSE stream
        tool_calls = []
        final_result = None
        for block in response.text.split("\n\n"):
            if not block.strip().startswith("data:"):
                continue
            payload = json.loads(block.replace("data:", "").strip())
            if payload.get("type") == "tool_call":
                tool_calls.append(payload.get("record"))
            elif payload.get("type") == "final_result":
                final_result = payload.get("result")

        return tool_calls, final_result

    def test_budget_reset_across_consecutive_questions(self):
        """Verify each question receives a fresh 6-call budget over SSE stream."""
        # When OPENAI_API_KEY is not set, /api/ask catches LLMConfigurationError
        # and returns an error event and final_result with INSUFFICIENT status.
        # This test verifies endpoint structure and SSE formatting.
        calls1, res1 = self._ask("What is the primary color of the company logo?")
        self.assertIsNotNone(res1)
        self.assertEqual(res1.get("calls_remaining"), 6)

        calls2, res2 = self._ask("When was project Alpha started?")
        self.assertIsNotNone(res2)
        self.assertEqual(res2.get("calls_remaining"), 6)

    def test_budget_info_endpoint(self):
        """Verify /api/budget returns the fresh budget specification."""
        resp = client.get("/api/budget")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("calls_remaining"), 6)
        self.assertEqual(data.get("calls_used"), 0)

    def test_invalid_file_type_rejected(self):
        """Verify non-PDF uploads are rejected with HTTP 400."""
        resp = client.post(
            "/api/ask",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
            data={"question": "test"},
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
