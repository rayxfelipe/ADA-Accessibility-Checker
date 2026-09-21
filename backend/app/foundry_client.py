"""Client wrapper around the Microsoft Foundry agent used to audit PDFs."""

import base64
import logging
import os
from dataclasses import dataclass

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

from . import config

logger = logging.getLogger("ada_checker.foundry_client")


class AgentAuditError(Exception):
    """Raised when the Foundry agent run fails or cannot be reached."""


@dataclass
class AuditResult:
    thread_id: str
    run_id: str
    response_text: str


def _get_credential():
    # DefaultAzureCredential is for local development (az login). In production,
    # prefer a managed identity - see Azure authentication best practices.
    if os.getenv("ENVIRONMENT", "development") == "development":
        return DefaultAzureCredential()
    client_id = os.getenv("AZURE_CLIENT_ID")
    return ManagedIdentityCredential(client_id=client_id) if client_id else ManagedIdentityCredential()


class FoundryAgentClient:
    """Lazily-initialized, cached client for the ADA Accessibility Checker agent."""

    def __init__(self):
        self._project_client: AIProjectClient | None = None
        self._openai_client = None

    @property
    def project_client(self) -> AIProjectClient:
        if self._project_client is None:
            self._project_client = AIProjectClient(
                endpoint=config.PROJECT_ENDPOINT,
                credential=_get_credential(),
            )
        return self._project_client

    @property
    def openai_client(self):
        if self._openai_client is None:
            self._openai_client = self.project_client.get_openai_client()
        return self._openai_client

    def _audit_with_responses_api(self, file_path: str, original_filename: str):
        with open(file_path, "rb") as pdf_file:
            encoded_pdf = base64.b64encode(pdf_file.read()).decode("ascii")

        return self.openai_client.responses.create(
            model=config.MODEL_DEPLOYMENT_NAME,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": original_filename,
                            "file_data": f"data:application/pdf;base64,{encoded_pdf}",
                        },
                        {
                            "type": "input_text",
                            "text": (
                                f"{config.AUDIT_PROMPT}\n\n"
                                f"Document name: {original_filename}"
                            ),
                        },
                    ],
                }
            ],
            extra_body={
                "agent_reference": {
                    "name": config.AGENT_NAME,
                    "type": "agent_reference",
                }
            },
        )

    def audit_pdf(self, file_path: str, original_filename: str) -> AuditResult:
        response = self._audit_with_responses_api(
            file_path,
            original_filename,
        )
        if not response.output_text:
            raise AgentAuditError("The agent did not return a response.")
        return AuditResult(
            thread_id=response.id,
            run_id=response.id,
            response_text=response.output_text,
        )


foundry_agent_client = FoundryAgentClient()
