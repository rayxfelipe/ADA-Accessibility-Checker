import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app import config
from app.foundry_client import FoundryAgentClient


class FoundryAgentClientTests(unittest.TestCase):
    def test_uses_v2_agent_reference_with_pdf_and_audit_prompt(self):
        client = FoundryAgentClient()
        create = Mock(return_value=SimpleNamespace(id="response-1", output_text="report"))
        client._openai_client = SimpleNamespace(responses=SimpleNamespace(create=create))

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_file:
            pdf_file.write(b"%PDF-1.7\n")
            pdf_path = pdf_file.name

        try:
            result = client.audit_pdf(pdf_path, "sample.pdf")
        finally:
            Path(pdf_path).unlink(missing_ok=True)

        request = create.call_args.kwargs
        self.assertEqual(request["model"], config.MODEL_DEPLOYMENT_NAME)
        self.assertEqual(
            request["extra_body"],
            {"agent_reference": {"name": config.AGENT_NAME, "type": "agent_reference"}},
        )
        self.assertIn(config.AUDIT_PROMPT, request["input"][0]["content"][1]["text"])
        self.assertEqual(result.response_text, "report")


if __name__ == "__main__":
    unittest.main()