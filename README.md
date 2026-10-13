# Policy That Changed — Grounded QA Assistant

A small, offline question-answering assistant over three merchant-service policy documents
(`policy_master_v1.md`, `circular_2026_08_amendment.md`, `merchant_faq_2026-03.md`).

## How to run

Requirements: Python 3.9+ (only stdlib + `python-dateutil` is optional; the code falls back).

```bash
# Ask one question (default as_of_date 2026-08-15)
python3 policy_assistant.py "When does a small merchant receive UPI money?"

# Ask with an explicit as_of_date
python3 policy_assistant.py "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?" --as-of 2026-09-05

# Run the built-in demo for all spec questions
python3 policy_assistant.py --demo

# Run evaluation
python3 run_eval.py
```

Programmatic use:

```python
from policy_assistant import ask
r = ask("Same merchant, a Rs.1,50,000 payment.", "2026-08-15")
# r -> {"answer": ..., "citations": [...], "status": "ANSWERED"|"CONFLICT_RESOLVED"|"CANNOT_ANSWER", "resolution": ...}
```

## What works

- Date-aware answers: the same question can yield different results depending on `as_of_date`
  (e.g. MDR reversal deleted from 01 Sep 2026).
- Deterministic arithmetic for MDR/GST/caps via `Decimal`, not LLM guessing.
- Cites real document + clause numbers (master clauses, circular amendments A–F, FAQ section).
- Says `CANNOT_ANSWER` instead of inventing clauses for out-of-scope questions.
- Works fully offline, no API key.

## What doesn't / known limits

- Natural language understanding is rule/keyword based, not semantic.
- Merchant size (small vs large) must be stated or inferred from wording; stateless calls
  cannot remember "same merchant" from a prior turn except via explicit phrases.
- No handling of bank holidays / working-day calendars for exact settlement dates.
- No document ingestion pipeline for new/changed documents; clauses are hard-coded expectations.
See `WHERE_IT_BREAKS.md`.
