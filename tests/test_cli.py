"""End-to-end tests for the fretfit command line interface."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fretfit import fit as fit_module, model, report as report_module

from helpers import document

ROOT = Path(__file__).resolve().parent.parent


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "fretfit", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def write(tmp: str, name: str, payload: dict) -> Path:
    path = Path(tmp) / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class FitCommandTests(unittest.TestCase):
    def test_fit_within_tolerance_exit_zero_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write(tmp, "measure.json", document(nut=-0.4, saddle=2.7))
            out = Path(tmp) / "report.json"
            proc = run("fit", "--input", str(source), "--json", str(out))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("fretfit:", proc.stdout)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"]["status"], "within-tolerance")
            self.assertTrue(payload["result"]["converged"])

    def test_out_of_tolerance_exit_one(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"] = [
            {"fret": 3, "cents": -16.0},
            {"fret": 8, "cents": 16.0},
            {"fret": 14, "cents": -16.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            source = write(tmp, "measure.json", payload)
            proc = run("fit", "--input", str(source))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("out-of-tolerance", proc.stdout)

    def test_invalid_input_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write(tmp, "bad.json", {"scale_length_mm": 10, "strings": []})
            proc = run("fit", "--input", str(source))
            self.assertEqual(proc.returncode, 2)
            self.assertIn("fretfit:", proc.stderr)

    def test_quiet_has_no_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write(tmp, "measure.json", document())
            proc = run("fit", "--input", str(source), "--quiet")
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.strip(), "")

    def test_render_is_ascii(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = write(tmp, "measure.json", document())
            proc = run("fit", "--input", str(source))
            proc.stdout.encode("ascii")


class VerifyCommandTests(unittest.TestCase):
    def _payload(self) -> dict:
        doc = model.parse(document(nut=-0.35, saddle=2.4))
        return report_module.build(doc, fit_module.fit(doc))

    def test_verify_accepts_report(self):
        ok, problems, summary = report_module.verify_report(self._payload())
        self.assertTrue(ok, problems)
        self.assertEqual(summary["strings"], 6)

    def test_verify_rejects_tampered_nut(self):
        payload = self._payload()
        payload["result"]["strings"][0]["nut_mm"] += 0.2
        ok, problems, _ = report_module.verify_report(payload)
        self.assertFalse(ok)
        self.assertTrue(any("nut_mm" in problem for problem in problems))

    def test_verify_rejects_tampered_residual(self):
        payload = self._payload()
        payload["result"]["strings"][0]["points"][0]["after_cents"] += 2.0
        ok, problems, _ = report_module.verify_report(payload)
        self.assertFalse(ok)
        self.assertTrue(any("after_cents" in problem for problem in problems))

    def test_verify_rejects_tampered_status(self):
        payload = self._payload()
        payload["result"]["status"] = "out-of-tolerance"
        ok, problems, _ = report_module.verify_report(payload)
        self.assertFalse(ok)
        self.assertTrue(any("status" in problem for problem in problems))

    def test_verify_command_exit_codes(self):
        payload = self._payload()
        with tempfile.TemporaryDirectory() as tmp:
            good = write(tmp, "report.json", payload)
            proc = run("verify", str(good))
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("verify: ok", proc.stdout)

            payload["result"]["summary"]["worst_after_cents"] += 5
            bad = write(tmp, "bad.json", payload)
            proc = run("verify", str(bad))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("verify: FAILED", proc.stdout)

    def test_verify_missing_file(self):
        proc = run("verify", "nope-report.json")
        self.assertEqual(proc.returncode, 2)

    def test_verify_rejects_foreign_report(self):
        ok, problems, _ = report_module.verify_report({"tool": "x"})
        self.assertFalse(ok)
        self.assertTrue(problems)


if __name__ == "__main__":
    unittest.main()
