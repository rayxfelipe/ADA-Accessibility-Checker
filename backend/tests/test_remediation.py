import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app import config
from app.main import app


class _FakeAsyncClient:
    def __init__(self, response: httpx.Response, **_kwargs):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, *_args, **_kwargs):
        return self.response


class RemediationProxyTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_url = config.REMEDIATOR_API_URL
        config.REMEDIATOR_API_URL = "https://remediator.example"

    def tearDown(self):
        config.REMEDIATOR_API_URL = self.original_url

    def test_returns_remediated_pdf(self):
        upstream = httpx.Response(200, content=b"%PDF-1.7\nremediated", headers={"content-type": "application/pdf"})
        report = json.dumps({"fileName": "sample.pdf", "remediationReport": "report"})
        with patch("app.main.httpx.AsyncClient", side_effect=lambda **kwargs: _FakeAsyncClient(upstream, **kwargs)):
            response = self.client.post(
                "/api/remediate",
                files={"file": ("sample.pdf", b"%PDF-1.7\nsource", "application/pdf")},
                data={"remediation_report": report},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.content, b"%PDF-1.7\nremediated")
        self.assertIn("sample_remediated.pdf", response.headers["content-disposition"])

    def test_rejects_mismatched_report(self):
        report = json.dumps({"fileName": "different.pdf", "remediationReport": "report"})
        response = self.client.post(
            "/api/remediate",
            files={"file": ("sample.pdf", b"%PDF-1.7\nsource", "application/pdf")},
            data={"remediation_report": report},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "The remediation report does not match the uploaded PDF.")

    def test_rejects_oversized_remediator_response(self):
        upstream = httpx.Response(
            200,
            content=b"%PDF-" + b"x" * config.REMEDIATOR_MAX_FILE_SIZE_BYTES,
            headers={"content-type": "application/pdf"},
        )
        report = json.dumps({"fileName": "sample.pdf", "remediationReport": "report"})
        with patch("app.main.httpx.AsyncClient", side_effect=lambda **kwargs: _FakeAsyncClient(upstream, **kwargs)):
            response = self.client.post(
                "/api/remediate",
                files={"file": ("sample.pdf", b"%PDF-1.7\nsource", "application/pdf")},
                data={"remediation_report": report},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "The remediation service returned an oversized PDF.")


if __name__ == "__main__":
    unittest.main()