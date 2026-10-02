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


def _evidence_tier(report: str) -> str:
    match = re.search(
        r"\bEvidence tier(?: reached)?\s*:\s*(Tier\s+[ABC](?:\s*[—-]\s*[^·\n]+)?)",
        report,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else "Not reported"


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
        rule_match = re.match(r"^([A-Z]\d+)\s+(.+)$", rule)
        rule_id = rule_match.group(1) if rule_match else ""
        requirement = rule_match.group(2) if rule_match else rule
        if not rule_id:
            warnings.append(f"Rule '{rule}' has no stable identifier.")
        elif rule_id in seen_ids:
            warnings.append(f"Rule identifier '{rule_id}' is duplicated.")
        seen_ids.add(rule_id)
        findings.append(
            {
                "ruleId": rule_id,
                "requirement": requirement,
                "severity": severity,
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
