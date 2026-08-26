"""Client wrapper around the Microsoft Foundry model used to audit PDFs."""

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
        self._agent_id: str | None = None

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
            self._openai_client = self.project_client.get_openai_client(
                api_version=config.OPENAI_API_VERSION
            )
        return self._openai_client

    def _resolve_agent_id(self) -> str:
        if self._agent_id:
            return self._agent_id
        agents_client = self.project_client.agents
        for agent in agents_client.list_agents():
            if agent.name == config.AGENT_NAME:
                self._agent_id = agent.id
                return self._agent_id
        raise AgentAuditError(
            f"Agent '{config.AGENT_NAME}' was not found in the Foundry project."
        )

    def audit_pdf(self, file_path: str, original_filename: str) -> AuditResult:
        agents_client = self.project_client.agents
        agent_id = self._resolve_agent_id()
        agent = agents_client.get_agent(agent_id)

        with open(file_path, "rb") as pdf_file:
            encoded_pdf = base64.b64encode(pdf_file.read()).decode("ascii")

        response = self.openai_client.responses.create(
            model=agent.model,
            instructions=agent.instructions or None,
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
        )
        if not response.output_text:
            raise AgentAuditError("The model did not return a response.")
        return AuditResult(
            thread_id=response.id,
            run_id=response.id,
            response_text=response.output_text,
        )


foundry_agent_client = FoundryAgentClient()
