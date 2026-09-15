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
    """Audit the attached PDF for WCAG 2.2 Level AA and Section 508/ADA. Return only
Markdown in the exact section order below. Replace each description in angle brackets
with audit content; do not emit placeholders, template notes, or an introduction.

# Accessibility Audit Report: <document title>

**Overall Status:** **<overall status>**

**Document Type:** <document type> · <page count> page(s)

**Audit Date:** <audit date>

**Audited By:** ADAAccessibilityCheckerAgent

**Standards Applied:** <standards applied>

**Audit Basis:** <what was directly inspected and the audit limitations>. If a real,
public source URL was supplied with the document, append a Markdown link whose label is
"<document title> | <document format>". Never invent a URL.

## Severity Summary

Use a Markdown table with columns Severity and Count. Include Critical, High, Medium,
Low, and Needs Human Review. Derive every count from the detailed findings and human
review items; never author or estimate summary values independently.

## Executive Summary

Write a concise narrative, followed by "The most significant concerns are:" and a
numbered list of the most significant concerns. Omit the list when there are none.

# Detailed Findings

Use a Markdown table with columns Location, Severity, Finding, Impacted Users,
WCAG / Best Practice, and Remediation. Use only Critical, High, Medium, or Low for
severity. Join multiple impacted-user groups and criteria with ", ". Keep each finding
and remediation specific and evidence-based. If a real evidence URL is available,
append a Markdown link labeled "<document title> | <document format>" inside the
Finding cell and escape its label separator as "\\|". Never invent an evidence URL.
Omit this entire section when there are no findings.

# Needs Human Review Items

For each item, use this structure, with a 1-based index:

### <index>. <title>

**Location:** <location>

**Verify:** <what a person must verify>

**Why it cannot be automated:** <reason>

Omit this entire section when no checks require human review.

# Visual References

Begin with a short introduction. Then list each reference as:
"- **Page <page>** — <caption>". Omit this entire section when there are no visual
references.

# Prioritized Fix List

Group fixes under "### Priority <priority> (<severity>)" headings. Under each heading,
use a numbered list of fixes in implementation order. Omit this entire section when
there are no fixes.

**Conclusion:** <concise conclusion>

Evidence rules:
- Report only findings supported by the attached PDF.
- Clearly distinguish directly observed evidence from assumptions.
- Put anything that cannot be verified from the available PDF in Needs Human Review.
- Do not claim that a visual PDF inspection proves tag-tree or assistive-technology
  behavior.
- Keep table cells concise and escape any literal pipe inside a table cell as "\\|".""",
)
