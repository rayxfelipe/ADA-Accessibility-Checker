"""Convert the agent's Markdown report into a stable assessment contract."""

from __future__ import annotations

import re
from typing import Any

from . import config

STATUS_KEYS = {
    "Passed": "pass",
    "Failed": "fail",
    "Needs manual check": "manual",
    "Skipped": "skipped",
}

RULE_CATALOG = (
    ("D1", "Accessibility permission flag"),
    ("D2", "Image-only PDF"),
    ("D3", "Tagged PDF"),
    ("D4", "Logical Reading Order"),
    ("D5", "Primary language"),
    ("D6", "Title"),
    ("D7", "Bookmarks"),
    ("D8", "Color contrast"),
    ("P1", "Tagged content"),
    ("P2", "Tagged annotations"),
    ("P3", "Tab order"),
    ("P4", "Character encoding"),
    ("P5", "Tagged multimedia"),
    ("P6", "Screen flicker"),
    ("P7", "Scripts"),
    ("P8", "Timed responses"),
    ("P9", "Navigation links"),
    ("F1", "Tagged form fields"),
    ("F2", "Field descriptions"),
    ("A1", "Figures alternate text"),
    ("A2", "Nested alternate text"),
    ("A3", "Associated with content"),
    ("A4", "Hides annotation"),
    ("A5", "Other elements alternate text"),
    ("T1", "Rows"),
    ("T2", "TH and TD"),
    ("T3", "Headers"),
    ("T4", "Regularity"),
    ("T5", "Summary"),
    ("L1", "List items"),
    ("L2", "Lbl and LBody"),
    ("H1", "Appropriate nesting"),
)

RULE_SEVERITIES = {
    **{rule_id: "Blocker" for rule_id in ("D1", "D2", "D3", "P1")},
    **{rule_id: "Critical" for rule_id in ("D5", "P3", "P4", "A1", "T1", "T2", "T3", "T4", "H1")},
    **{rule_id: "Major" for rule_id in ("D6", "P2", "P9", "F1", "F2", "A2", "A3", "A4", "A5", "L1", "L2")},
    **{rule_id: "Minor" for rule_id in ("D7", "T5")},
}

STRICT_EVIDENCE_RULE_IDS = {"A5"}


def _field(report: str, label: str) -> str | None:
    escaped = re.escape(label)
    match = re.search(
        rf"^\s*(?:\*\*)?{escaped}:(?:\*\*)?\s*(.+?)\s*$",
        report,
        re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else None


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_divider(line: str) -> bool:
    cells = _table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _summary_rows(report: str) -> list[list[str]]:
    lines = report.splitlines()
    for index in range(len(lines) - 1):
        headers = _table_cells(lines[index])
        if (
            len(headers) != 3
            or [header.lower() for header in headers] != ["rule", "severity", "status"]
            or not _is_divider(lines[index + 1])
        ):
            continue
        rows = []
        for line in lines[index + 2:]:
            if not line.strip().startswith("|"):
                break
            cells = _table_cells(line)
            if len(cells) == 3:
                rows.append(cells)
        return rows
    return []


def _failure_rows(report: str) -> list[list[str]]:
    lines = report.splitlines()
    expected_headers = [
        "rule",
        "severity",
        "pages",
        "count",
        "tag path/object",
        "wcag / best practice",
        "remediation",
    ]
    for index in range(len(lines) - 1):
        headers = _table_cells(lines[index])
        if (
            [header.lower() for header in headers] != expected_headers
            or not _is_divider(lines[index + 1])
        ):
            continue
        rows = []
        for line in lines[index + 2:]:
            if not line.strip().startswith("|"):
                break
            cells = _table_cells(line)
            if len(cells) == len(expected_headers):
                rows.append(cells)
        return rows
    return []


def _evidence_tier(report: str) -> str:
    match = re.search(
        r"\bEvidence tier(?: reached)?\s*:\s*(Tier\s+[ABC](?:\s*[—-]\s*[^·\n]+)?)",
        report,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else "Not reported"


def _canonical_rule(rule: str) -> tuple[str, str]:
    explicit_id = re.match(r"^([A-Z]\d+)\s+(.+)$", rule)
    candidate = explicit_id.group(2) if explicit_id else rule
    normalized = re.sub(r"\s+", " ", candidate).strip().casefold()
    for rule_id, requirement in RULE_CATALOG:
        canonical = requirement.casefold()
        if normalized == canonical or normalized.startswith(f"{canonical} "):
            return rule_id, candidate
    return (explicit_id.group(1), candidate) if explicit_id else ("", candidate)


def validate_assessment(report: str, assessment: dict[str, Any]) -> list[str]:
    """Return contract errors that make an assessment unsafe to display."""
    errors = []
    findings = assessment.get("findings", [])
    if len(findings) != config.EXPECTED_RULE_COUNT:
        errors.append(
            f"Expected {config.EXPECTED_RULE_COUNT} rule rows but found {len(findings)}."
        )

    rule_ids = [finding.get("ruleId") for finding in findings]
    if any(not rule_id for rule_id in rule_ids):
        errors.append("Every finding must have a stable rule identifier.")
    if len(set(rule_ids)) != len(rule_ids):
        errors.append("Finding rule identifiers must be unique.")

    failure_evidence = {}
    for rule, _severity, pages, count, location, _standard, _remediation in _failure_rows(report):
        rule_id, _requirement = _canonical_rule(rule)
        if rule_id:
            failure_evidence[rule_id] = (pages, count, location)

    for finding in findings:
        rule_id = finding.get("ruleId")
        if finding.get("status") != "fail" or rule_id not in STRICT_EVIDENCE_RULE_IDS:
            continue
        evidence = failure_evidence.get(rule_id)
        if evidence is None:
            errors.append(f"{rule_id} is Failed without a failures-table evidence row.")
            continue
        pages, count, location = evidence
        has_page = bool(re.search(r"\b\d+\b", pages))
        has_count = bool(re.fullmatch(r"\d+", count)) and int(count) > 0
        hypothetical = bool(re.search(r"\bif present\b|\bany .+ cannot\b", location, re.IGNORECASE))
        if not has_page or not has_count or hypothetical:
            errors.append(
                f"{rule_id} is Failed without a concrete page, positive count, and located defect."
            )
    return errors


def parse_assessment(report: str) -> dict[str, Any]:
    """Return structured metadata and findings derived from one report table."""
    findings = []
    warnings = []
    seen_ids: set[str] = set()

    for rule, severity, raw_status in _summary_rows(report):
        status_label = re.sub(r"\s*\[[^]]+]\s*$", "", raw_status).strip()
        status = STATUS_KEYS.get(status_label)
        if status is None:
            warnings.append(f"Unsupported status '{raw_status}' for '{rule}'.")
            continue
        rule_id, requirement = _canonical_rule(rule)
        if not rule_id:
            warnings.append(f"Rule '{rule}' has no stable identifier.")
        elif rule_id in seen_ids:
            warnings.append(f"Rule identifier '{rule_id}' is duplicated.")
        seen_ids.add(rule_id)
        findings.append(
            {
                "ruleId": rule_id,
                "requirement": requirement,
                "severity": RULE_SEVERITIES.get(rule_id, severity),
                "status": status,
                "statusLabel": status_label,
            }
        )

    standards = _field(report, "Standards Applied")
    if standards is None:
        standards = config.STANDARDS_APPLIED
        warnings.append("The agent omitted Standards Applied; the configured audit baseline was used.")
    if len(findings) != config.EXPECTED_RULE_COUNT:
        warnings.append(
            f"Expected {config.EXPECTED_RULE_COUNT} rule rows but found {len(findings)}."
        )

    summary = {key: 0 for key in STATUS_KEYS.values()}
    for finding in findings:
        summary[finding["status"]] += 1

    return {
        "checkerVersion": config.CHECKER_VERSION,
        "standardsApplied": standards,
        "overallStatus": _field(report, "Overall Status") or "Not reported",
        "evidenceTier": _evidence_tier(report),
        "summary": summary,
        "findings": findings,
        "warnings": warnings,
    }
