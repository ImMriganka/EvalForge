#!/usr/bin/env python3
"""
Regression gate — reads the pytest JSON report produced by the backend-tests
job and fails CI if quality thresholds are not met.

Thresholds:
  PASS_RATE  = 1.0   (100% — no failures tolerated)
  MIN_TESTS  = 69    (guard against tests being accidentally deleted)

Usage:
  python scripts/check_regression.py <path-to-pytest-report.json>
"""
import json
import sys


PASS_RATE = 1.0   # fraction — 1.0 = 100%
MIN_TESTS = 69    # minimum expected test count


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check_regression.py <pytest-report.json>")
        sys.exit(1)

    report_path = sys.argv[1]
    try:
        with open(report_path) as f:
            report = json.load(f)
    except FileNotFoundError:
        print(f"Report not found: {report_path}")
        sys.exit(1)

    summary = report.get("summary", {})
    total   = summary.get("total",   0)
    passed  = summary.get("passed",  0)
    failed  = summary.get("failed",  0)
    errors  = summary.get("error",   0)
    rate    = passed / total if total > 0 else 0.0

    print(f"Results: {passed}/{total} passed ({rate:.1%})  |  failed={failed}  error={errors}")

    issues = []

    if rate < PASS_RATE:
        issues.append(
            f"Pass rate {rate:.1%} is below the required {PASS_RATE:.0%}  "
            f"({failed} failure(s), {errors} error(s))"
        )

    if total < MIN_TESTS:
        issues.append(
            f"Only {total} tests collected — expected at least {MIN_TESTS}. "
            "Tests may have been accidentally removed."
        )

    if issues:
        print("\nREGRESSION GATE FAILED")
        for issue in issues:
            print(f"  ✗ {issue}")
        sys.exit(1)

    print("Regression gate passed.")


if __name__ == "__main__":
    main()
