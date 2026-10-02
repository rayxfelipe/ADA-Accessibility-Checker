import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.foundry_client import AuditResult
from app.main import _run_audit_job, audit_jobs, audit_jobs_lock


class AuditJobTests(unittest.TestCase):
    def test_retries_once_when_report_evidence_is_invalid(self):
        job_id = "retry-job"
        with audit_jobs_lock:
            audit_jobs[job_id] = {"jobId": job_id, "status": "queued"}

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_file:
            pdf_file.write(b"%PDF-1.7\n")
            pdf_path = pdf_file.name

        results = [
            AuditResult("response-1", "response-1", "invalid report"),
            AuditResult("response-2", "response-2", "corrected report"),
        ]
        try:
            with (
                patch("app.main.foundry_agent_client.audit_pdf", side_effect=results) as audit_pdf,
                patch("app.main.parse_assessment", side_effect=[{"findings": []}, {"findings": []}]),
                patch(
                    "app.main.validate_assessment",
                    side_effect=[["A5 lacks concrete evidence."], []],
                ),
            ):
                _run_audit_job(job_id, pdf_path, "sample.pdf")

            self.assertEqual(audit_jobs[job_id]["status"], "completed")
            self.assertEqual(audit_jobs[job_id]["runId"], "response-2")
            self.assertEqual(audit_pdf.call_count, 2)
            self.assertIn("prior response failed contract validation", audit_pdf.call_args.args[2])
        finally:
            Path(pdf_path).unlink(missing_ok=True)
            with audit_jobs_lock:
                audit_jobs.pop(job_id, None)


if __name__ == "__main__":
    unittest.main()
