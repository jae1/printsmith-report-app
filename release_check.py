"""Read-only accounting checks and explicitly approved local release snapshots."""

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
REPORT_DATES = (
    "2024-05-24", "2024-06-03", "2026-06-16", "2026-06-18", "2026-06-22",
    "2026-07-15", "2026-07-24", "2026-09-30", "2026-10-02", "2026-11-04",
    "2026-11-10", "2026-11-11",
)
READ_ONLY_OPTIONS = "-c default_transaction_read_only=on -c statement_timeout=30000"
RUN_SUITE = """
import sys, unittest
sys.path.insert(0, sys.argv[1])
suite = unittest.defaultTestLoader.discover(sys.argv[2], pattern=sys.argv[3])
if suite.countTestCases() < int(sys.argv[4]):
    raise SystemExit('Required regression tests are missing')
result = unittest.TextTestRunner(verbosity=2).run(suite)
if sys.argv[3] == 'test_batch_payment.py' and result.skipped:
    raise SystemExit('Live release checks must not be skipped')
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


def run_tests(live=False):
    env = dict(os.environ)
    env["PRINTSMITH_LIVE_TESTS"] = "1" if live else "0"
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PGOPTIONS"] = READ_ONLY_OPTIONS
    env["PGCONNECT_TIMEOUT"] = "10"
    pattern, minimum = ("test_batch_payment.py", 8) if live else ("test_*.py", 1)
    subprocess.run(
        [sys.executable, "-c", RUN_SUITE, str(ROOT), str(ROOT / "tests"), pattern, str(minimum)],
        env=env, check=True,
    )


def accounting_snapshot(report_dates, get_report_data=None):
    if get_report_data is None:
        from app.services.report_service import get_report_data

    reports = {}
    for report_date in report_dates:
        data = get_report_data(date.fromisoformat(report_date))
        sections = {}
        for section in ("paid", "new_today"):
            rows = []
            for item in data[section]:
                try:
                    amount = Decimal(str(item["grandtotal"]))
                    if not amount.is_finite():
                        raise ValueError("non-finite amount")
                    amount = amount.quantize(Decimal("0.01"))
                except (InvalidOperation, ValueError) as error:
                    raise ValueError(f"Invalid amount on {report_date}, invoice {item['invoicenumber']}") from error
                row = {
                    "invoice": str(item["invoicenumber"]),
                    "amount": str(abs(amount) if amount == 0 else amount),
                }
                if section == "paid":
                    row.update(method=item["pay_method_display"], type=item["transaction_type"])
                rows.append(row)
            sections[section] = sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
        reports[report_date] = sections
    return {"format": 1, "reports": reports}


def write_snapshot(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(data, output, indent=2, sort_keys=True, allow_nan=False)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def snapshot_difference(expected, actual):
    return "".join(difflib.unified_diff(
        json.dumps(expected, indent=2, sort_keys=True).splitlines(keepends=True),
        json.dumps(actual, indent=2, sort_keys=True).splitlines(keepends=True),
        fromfile="approved baseline", tofile="candidate release",
    ))


def check_release(baseline_path, write_baseline=False):
    baseline_path = Path(baseline_path)
    run_tests()
    if not write_baseline and not baseline_path.exists():
        raise ValueError(f"Approved baseline missing: {baseline_path}. Review reports before explicitly using --write-baseline.")

    expected = None
    if not write_baseline:
        expected = json.loads(baseline_path.read_text(encoding="utf-8"))
        if (not isinstance(expected, dict) or expected.get("format") != 1
                or not isinstance(expected.get("reports"), dict)
                or set(expected["reports"]) != set(REPORT_DATES)):
            raise ValueError("Baseline has an unsupported format or missing representative dates")

    run_tests(live=True)
    os.environ["PGOPTIONS"] = READ_ONLY_OPTIONS
    os.environ["PGCONNECT_TIMEOUT"] = "10"
    actual = accounting_snapshot(REPORT_DATES)
    if write_baseline:
        write_snapshot(baseline_path, actual)
        print(f"Baseline captured: {baseline_path}. Review it before enabling deployment.")
        return 0

    candidate_path = Path(str(baseline_path) + ".candidate.json")
    diff_path = Path(str(baseline_path) + ".diff.txt")
    difference = snapshot_difference(expected, actual)
    if difference:
        write_snapshot(candidate_path, actual)
        diff_path.write_text(difference, encoding="utf-8")
        print(f"Accounting changed; deployment blocked. Review {diff_path} and {candidate_path}.", file=sys.stderr)
        return 1
    for path in (candidate_path, diff_path):
        path.unlink(missing_ok=True)
    print("Offline tests, live payment regressions, and accounting baseline passed.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--write-baseline", action="store_true", help="Explicitly capture/replace the local baseline after report review")
    args = parser.parse_args(argv)
    try:
        return check_release(args.baseline, args.write_baseline)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Release check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
