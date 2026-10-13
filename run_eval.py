#!/usr/bin/env python3
"""Run the assistant against eval.json and print a score table."""
import json
from pathlib import Path

from policy_assistant import ask

EVAL = Path(__file__).resolve().parent / "eval.json"


def score_one(item, result):
    checks = {}
    # status
    checks["status"] = (result["status"] == item.get("expected_status"))
    # citations: each expected citation string must be a substring of some returned citation
    returned_cites = " | ".join(result.get("citations", [])).lower()
    cite_ok = True
    for ec in item.get("expected_citations", []):
        if ec.lower() not in returned_cites:
            cite_ok = False
            break
    # for CANNOT_ANSWER with no expected citations, require none? just pass if none expected
    if not item.get("expected_citations"):
        cite_ok = True
    checks["citations"] = cite_ok
    # answer contains
    ans_low = result.get("answer", "").lower()
    ans_ok = True
    for sub in item.get("expected_answer_contains", []):
        if sub.lower() not in ans_low:
            ans_ok = False
            break
    checks["answer"] = ans_ok
    passed = all(checks.values())
    return passed, checks


def main():
    items = json.loads(EVAL.read_text(encoding="utf-8"))
    rows = []
    total_pass = 0
    for item in items:
        res = ask(item["question"], item["as_of_date"])
        passed, checks = score_one(item, res)
        total_pass += int(passed)
        rows.append((item["id"], "PASS" if passed else "FAIL", res["status"], checks))
    # print table
    print(f"{'ID':<28}{'RESULT':<8}{'STATUS':<20}CHECKS")
    print("-" * 70)
    for rid, res, status, checks in rows:
        chk = " ".join(f"{k}:{'Y' if v else 'N'}" for k, v in checks.items())
        print(f"{rid:<28}{res:<8}{status:<20}{chk}")
    print("-" * 70)
    print(f"Passed {total_pass}/{len(items)}")
    # details for failures
    for item in items:
        res = ask(item["question"], item["as_of_date"])
        passed, checks = score_one(item, res)
        if not passed:
            print(f"\n[FAIL] {item['id']}: {item['question']}")
            print(f"  status expected {item['expected_status']} got {res['status']}")
            print(f"  checks {checks}")
            print(f"  answer: {res['answer'][:300]}")


if __name__ == "__main__":
    main()
