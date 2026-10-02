import unittest

from app import config
from app.report_contract import parse_assessment


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


if __name__ == "__main__":
    unittest.main()
