"""Zero-dependency test runner.

Runs the test suite without pytest, so the pipeline can be verified with only
the standard library:

    python agents/guidelines/tests/run_all.py

(For the richer report, `python -m pytest agents/guidelines/tests` works too.)
"""

from __future__ import annotations

import os
import sys
import traceback

# Put the repo root on sys.path so `agents.guidelines` imports cleanly.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agents.guidelines.tests import (  # noqa: E402
    test_contract,
    test_fertility_gap,
    test_grade_integrity,
    test_triage_and_matcher,
)


def _run_module(module) -> tuple[int, int]:
    passed = failed = 0
    for name in sorted(dir(module)):
        if not name.startswith("test_"):
            continue
        fn = getattr(module, name)
        if not callable(fn):
            continue
        try:
            fn()
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {module.__name__}.{name}")
            traceback.print_exc()
        else:
            passed += 1
            print(f"  ok    {module.__name__}.{name}")
    return passed, failed


def main() -> int:
    total_passed = total_failed = 0
    for module in (
        test_triage_and_matcher,
        test_contract,
        test_fertility_gap,
        test_grade_integrity,
    ):
        print(f"\n{module.__name__}:")
        p, f = _run_module(module)
        total_passed += p
        total_failed += f

    print("\n" + "=" * 48)
    print(f"passed: {total_passed}   failed: {total_failed}")
    return 1 if total_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
