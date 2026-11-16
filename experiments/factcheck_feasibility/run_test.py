"""Run the 10-pair fact-check feasibility test against the real checker model."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from app import config
from app.summarize.factcheck import check


def main():
    if config.OFFLINE_MODE:
        sys.exit("Set OFFLINE_MODE=0 in .env to call the real checker.")

    pairs = json.loads((HERE / "pairs.json").read_text())
    results, caught, planted, false_flags = [], 0, 0, 0

    for p in pairs:
        r = check(p["summary"], p["source"])
        has_error = p["planted_error"] is not None
        if has_error:
            planted += 1
            caught += int(not r.passed)
        else:
            false_flags += int(not r.passed)
        results.append({"id": p["id"], "planted_error": p["planted_error"],
                        "passed": r.passed, "unsupported_claims": r.unsupported_claims})
        print(f"#{p['id']:>2}  planted={'yes' if has_error else 'no ':<3}  "
              f"checker={'PASS' if r.passed else 'FLAG'}  {r.unsupported_claims}")

    recall = caught / planted if planted else 0
    print(f"\nCaught {caught}/{planted} planted errors (recall {recall:.0%}); "
          f"{false_flags} false flags on faithful summaries.")
    print("Check by hand that each flag names the actual planted claim.")
    print("Target: >= 5/6 caught." + ("  PASS" if caught >= 5 else "  NOT MET"))

    (HERE / "results.json").write_text(json.dumps(
        {"model": config.FACTCHECK_MODEL, "caught": caught, "planted": planted,
         "false_flags": false_flags, "results": results}, indent=2))


if __name__ == "__main__":
    main()
