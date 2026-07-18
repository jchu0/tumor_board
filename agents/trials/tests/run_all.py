"""Zero-dependency test runner for the trials agent.

    python agents/trials/tests/run_all.py
"""

from __future__ import annotations

import os
import sys
import traceback

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agents.trials.tests import test_verdicts  # noqa: E402


def main() -> int:
    passed = failed = 0
    for name in sorted(dir(test_verdicts)):
        if not name.startswith("test_"):
            continue
        fn = getattr(test_verdicts, name)
        if not callable(fn):
            continue
        try:
            fn()
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {name}")
            traceback.print_exc()
        else:
            passed += 1
            print(f"  ok    {name}")
    print("\n" + "=" * 48)
    print(f"passed: {passed}   failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
