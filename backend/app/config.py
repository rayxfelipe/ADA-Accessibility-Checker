"""Configuration for the ADA Accessibility Checker backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Microsoft Foundry project connection
PROJECT_ENDPOINT = os.getenv(
    "PROJECT_ENDPOINT",
    "https://adaaccessibilitychecker-resource.services.ai.azure.com/api/projects/adaaccessibilitychecker",
)
AGENT_NAME = os.getenv("AGENT_NAME", "ADAAccessibilityCheckerAgent")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2025-04-01-preview")

# Upload constraints
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# CORS - comma separated list of allowed origins, "*" allows any origin
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# The instruction sent alongside the uploaded PDF on every audit request
AUDIT_PROMPT = os.getenv(
    "AUDIT_PROMPT",
    "Audit the attached PDF document for ADA (Americans with Disabilities Act) and "
    "WCAG (Web Content Accessibility Guidelines) compliance. Identify every "
    "accessibility issue you find, cite the relevant WCAG success criterion, rate "
    "each issue's severity (Critical, Serious, Moderate, or Minor), and provide "
    "clear, actionable remediation guidance for each issue. Finish with a brief "
    "overall summary of the document's accessibility posture.",
)
