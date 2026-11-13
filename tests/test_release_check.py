import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import release_check


def report(amount=100):
    return {
        "paid": [{"invoicenumber": "100", "grandtotal": amount,
                  "pay_method_display": "Check", "transaction_type": "PAID",
                  "current_balance": 999, "account_display": "Private customer"}],
        "new_today": [{"invoicenumber": "101", "grandtotal": 250}],
        "ready": [{"invoicenumber": "102", "grandtotal": 900}],
    }


class ReleaseCheckTests(unittest.TestCase):
    def test_runner_tests_candidate_source_while_preserving_runtime_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime, candidate = Path(directory) / "runtime", Path(directory) / "candidate"
            runtime.mkdir()
            (candidate / "tests").mkdir(parents=True)
            (runtime / "release_marker.py").write_text("VERSION = 'old checkout'\n")
            (candidate / "release_marker.py").write_text("VERSION = 'candidate'\n")
            (candidate / "tests/test_source.py").write_text(
                "import unittest, release_marker\n"
                "class Tests(unittest.TestCase):\n"
                " def test_source(self): self.assertEqual(release_marker.VERSION, 'candidate')\n"
            )
            env = dict(os.environ, PYTHONPATH=str(candidate))
            result = subprocess.run(
                [release_check.sys.executable, "-c", release_check.RUN_SUITE,
                 str(candidate), str(candidate / "tests"), "test_source.py", "1"],
                cwd=runtime, env=env, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_money_cannot_be_captured_or_compared_as_a_baseline(self):
        for amount in (float("nan"), float("inf"), float("-inf"), "invalid"):
            with self.subTest(amount=amount), tempfile.TemporaryDirectory() as directory, \
                    patch.object(release_check, "run_tests"):
                baseline = Path(directory) / "approved.json"
                with self.assertRaises(ValueError):
                    release_check.accounting_snapshot(["2026-11-04"], lambda day: report(amount))
                expected = release_check.accounting_snapshot(release_check.REPORT_DATES, lambda day: report())
                with patch("app.services.report_service.get_report_data", return_value=report(amount)):
                    self.assertEqual(release_check.main(["--baseline", str(baseline), "--write-baseline"]), 1)
                    self.assertFalse(baseline.exists())
                    release_check.write_snapshot(baseline, expected)
                    self.assertEqual(release_check.main(["--baseline", str(baseline)]), 1)

    def test_snapshot_compares_money_without_mutable_queues_or_private_names(self):
        first = release_check.accounting_snapshot(["2026-11-04"], lambda day: report(100.0))
        changed_context = report(100)
        changed_context["paid"][0]["current_balance"] = 0
        changed_context["ready"] = []
        second = release_check.accounting_snapshot(["2026-11-04"], lambda day: changed_context)
        self.assertEqual(first, second)
        self.assertEqual(first["reports"]["2026-11-04"]["paid"][0]["amount"], "100.00")
        self.assertNotIn("Private customer", json.dumps(first))

    def test_missing_baseline_blocks_before_live_access(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(release_check, "run_tests") as tests, \
                patch.object(release_check, "accounting_snapshot") as snapshot:
            result = release_check.main(["--baseline", str(Path(directory) / "missing.json")])
        self.assertEqual(result, 1)
        tests.assert_called_once_with()
        snapshot.assert_not_called()

    def test_changed_invoice_blocks_and_preserves_approved_baseline(self):
        expected = release_check.accounting_snapshot(release_check.REPORT_DATES, lambda day: report())
        actual = release_check.accounting_snapshot(release_check.REPORT_DATES, lambda day: report(200))
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(release_check, "run_tests") as tests, \
                patch.object(release_check, "accounting_snapshot", return_value=actual):
            baseline = Path(directory) / "approved.json"
            release_check.write_snapshot(baseline, expected)
            result = release_check.check_release(baseline)
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(baseline.read_text()), expected)
            self.assertEqual(json.loads(Path(str(baseline) + ".candidate.json").read_text()), actual)
            self.assertIn('"amount": "200.00"', Path(str(baseline) + ".diff.txt").read_text())
            self.assertEqual(tests.call_args_list, [unittest.mock.call(), unittest.mock.call(live=True)])

    def test_matching_baseline_passes_and_removes_stale_candidate_outputs(self):
        snapshot = release_check.accounting_snapshot(release_check.REPORT_DATES, lambda day: report())
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(release_check, "run_tests"), \
                patch.object(release_check, "accounting_snapshot", return_value=snapshot):
            baseline = Path(directory) / "approved.json"
            release_check.write_snapshot(baseline, snapshot)
            outputs = [Path(str(baseline) + suffix) for suffix in (".candidate.json", ".diff.txt")]
            for path in outputs:
                path.write_text("stale")
            self.assertEqual(release_check.check_release(baseline), 0)
            self.assertTrue(all(not path.exists() for path in outputs))

    def test_empty_or_wrong_format_baseline_cannot_disable_comparisons(self):
        for baseline_data in ({"format": 1, "reports": {}}, {"format": 2, "reports": {}}, []):
            with self.subTest(baseline=baseline_data), tempfile.TemporaryDirectory() as directory, \
                    patch.object(release_check, "run_tests"), \
                    patch.object(release_check, "accounting_snapshot") as snapshot:
                baseline = Path(directory) / "approved.json"
                release_check.write_snapshot(baseline, baseline_data)
                self.assertEqual(release_check.main(["--baseline", str(baseline)]), 1)
                snapshot.assert_not_called()

    def test_explicit_capture_runs_checks_and_writes_baseline(self):
        snapshot = release_check.accounting_snapshot(release_check.REPORT_DATES, lambda day: report())
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(release_check, "run_tests") as tests, \
                patch.object(release_check, "accounting_snapshot", return_value=snapshot):
            baseline = Path(directory) / "approved.json"
            self.assertEqual(release_check.main(["--baseline", str(baseline), "--write-baseline"]), 0)
            self.assertEqual(json.loads(baseline.read_text()), snapshot)
            self.assertEqual(tests.call_args_list, [unittest.mock.call(), unittest.mock.call(live=True)])

    def test_test_failure_prevents_snapshot_approval(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(release_check, "run_tests", side_effect=subprocess.CalledProcessError(1, "tests")), \
                patch.object(release_check, "accounting_snapshot") as snapshot:
            baseline = Path(directory) / "approved.json"
            self.assertEqual(release_check.main(["--baseline", str(baseline), "--write-baseline"]), 1)
            self.assertFalse(baseline.exists())
            snapshot.assert_not_called()

    def test_live_runner_explicitly_enables_read_only_regressions(self):
        with patch.object(subprocess, "run") as run:
            release_check.run_tests(live=True)
        args, kwargs = run.call_args
        self.assertEqual(args[0][-2:], ["test_batch_payment.py", "8"])
        self.assertEqual(kwargs["env"]["PRINTSMITH_LIVE_TESTS"], "1")
        self.assertIn("default_transaction_read_only=on", kwargs["env"]["PGOPTIONS"])
        self.assertTrue(kwargs["check"])

    def test_live_runner_rejects_a_suite_that_skips_its_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "test_batch_payment.py").write_text(
                "import unittest\n@unittest.skip('disabled')\nclass Tests(unittest.TestCase):\n"
                + "".join(f" def test_{number}(self): pass\n" for number in range(8))
            )
            result = subprocess.run(
                [release_check.sys.executable, "-c", release_check.RUN_SUITE, directory, directory, "test_batch_payment.py", "8"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not be skipped", result.stderr)

    def test_failed_atomic_write_leaves_baseline_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "approved.json"
            baseline.write_text("approved")
            with patch.object(os, "replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    release_check.write_snapshot(baseline, {"candidate": True})
            self.assertEqual(baseline.read_text(), "approved")
            self.assertEqual(list(Path(directory).iterdir()), [baseline])
