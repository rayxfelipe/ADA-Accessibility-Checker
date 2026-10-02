import unittest

from app import config
from app.report_contract import parse_assessment, validate_assessment


def _report(standards_line: str) -> str:
    rows = [
        "| Rule | Severity | Status |",
        "|---|---|---|",
        "| D1 Accessibility permission flag | Blocker | Passed |",
        "| D3 Tagged PDF | Blocker | Failed |",
        "| D4 Logical Reading Order | Major | Needs manual check |",
        "| T5 Summary | Minor | Skipped |",
    ]
    return "\n".join(
        [
            "Overall Status: CONFORMANCE NOT ESTABLISHED",
            standards_line,
            "File name: sample.pdf · Evidence tier: Tier B — content-level inspection",
            *rows,
        ]
    )


def _complete_report(a5_status: str, a5_evidence: str) -> str:
    from app.report_contract import RULE_CATALOG

    rows = ["| Rule | Severity | Status |", "|---|---|---|"]
    for rule_id, requirement in RULE_CATALOG:
        status = a5_status if rule_id == "A5" else "Passed"
        rows.append(f"| {rule_id} {requirement} | Major | {status} |")
    failures = [
        "| Rule | Severity | Pages | Count | Tag path/object | WCAG / Best Practice | Remediation |",
        "|---|---|---|---|---|---|---|",
    ]
    if a5_status == "Failed":
        failures.append(
            f"| A5 Other elements alternate text | Major | 1 | {a5_evidence} | "
            "page 1 object | WCAG 1.1.1 | Add alternate text |"
        )
    return "\n".join(
        [
            "Standards Applied: WCAG 2.1 A and AA",
            *rows,
            "### Failures table",
            *failures,
        ]
    )


class ReportContractTests(unittest.TestCase):
    def test_parses_plain_context_and_derives_counts_from_findings(self):
        assessment = parse_assessment(_report("Standards Applied: WCAG 2.1 A and AA"))

        self.assertEqual(assessment["standardsApplied"], "WCAG 2.1 A and AA")
        self.assertEqual(assessment["evidenceTier"], "Tier B — content-level inspection")
        self.assertEqual(
            assessment["summary"],
            {"pass": 1, "fail": 1, "manual": 1, "skipped": 1},
        )
        self.assertEqual(assessment["findings"][1]["ruleId"], "D3")
        self.assertEqual(assessment["findings"][1]["status"], "fail")

    def test_parses_bold_context(self):
        assessment = parse_assessment(_report("**Standards Applied:** WCAG 2.1 A and AA"))

        self.assertEqual(assessment["standardsApplied"], "WCAG 2.1 A and AA")

    def test_uses_configured_baseline_when_agent_omits_standards(self):
        assessment = parse_assessment(_report("Assessment basis omitted"))

        self.assertEqual(assessment["standardsApplied"], config.STANDARDS_APPLIED)
        self.assertIn("configured audit baseline", assessment["warnings"][0])

    def test_assigns_canonical_ids_when_agent_omits_them(self):
        report = "\n".join(
            [
                "Standards Applied: WCAG 2.1 A and AA",
                "| Rule | Severity | Status |",
                "|---|---|---|",
                "| Character encoding (Unicode-mapped) | — | Failed |",
                "| List items (LI direct child of L) | Major | Failed |",
                "| Lbl and LBody (LI contains only Lbl and LBody) | Major | Failed |",
            ]
        )

        assessment = parse_assessment(report)

        self.assertEqual(
            [finding["ruleId"] for finding in assessment["findings"]],
            ["P4", "L1", "L2"],
        )
        self.assertEqual(assessment["findings"][0]["severity"], "Critical")
        self.assertNotIn("no stable identifier", " ".join(assessment["warnings"]))

    def test_rejects_content_triggered_failure_without_positive_count(self):
        report = _complete_report("Failed", "—")
        assessment = parse_assessment(report)

        self.assertIn(
            "A5 is Failed without a concrete page, positive count, and located defect.",
            validate_assessment(report, assessment),
        )

    def test_accepts_content_triggered_failure_with_concrete_evidence(self):
        report = _complete_report("Failed", "1")
        assessment = parse_assessment(report)

        self.assertEqual(validate_assessment(report, assessment), [])


if __name__ == "__main__":
    unittest.main()
