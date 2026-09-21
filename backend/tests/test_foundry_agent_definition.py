import json
import unittest
from pathlib import Path

from app import config


class FoundryAgentDefinitionTests(unittest.TestCase):
    def test_manifest_matches_checker_contract(self):
        manifest_path = Path(__file__).resolve().parents[2] / "foundry" / "ADAAccessibilityCheckerAgent.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "ADAAccessibilityCheckerAgent")
        self.assertEqual(manifest["kind"], "prompt")
        self.assertEqual(manifest["model"], "gpt-5")
        self.assertEqual(manifest["instructionsSource"], "backend/app/config.py:AUDIT_PROMPT")
        self.assertIn("32-rule checker tree", manifest["instructions"])
        self.assertIn("## RULE CATALOG — the 32 Acrobat Full Check rules", config.AUDIT_PROMPT)
        self.assertIn("### ACCESSIBILITY CHECKER TREE", config.AUDIT_PROMPT)


if __name__ == "__main__":
    unittest.main()