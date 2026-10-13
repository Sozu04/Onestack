A Merchant Policy Assistant

This project is a small offline question-answering assistant for merchant service policies.
It reads three policy documents and answers questions about:

- UPI and card settlement
- MDR and GST calculations
- Refunds and chargebacks
- Payment limits
- Account closure

The assistant uses fixed rules from the policy documents. It does not use an API or an online AI
service.

## Requirements

- Python 3.9 or newer
- Internet access only for installing the Python packages

## Setup

Open a terminal in this folder and create a virtual environment:


Install the required packages:

```bash

pip install -r requirements.txt
```

## Run from the terminal

Ask one question:

```bash
python policy_assistant.py "When does a small merchant receive UPI money?"
```

Use a specific policy date:

```bash
python policy_assistant.py \
  "A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?" \
  --as-of 2026-09-05
```

Run the built-in demo:

```bash
python policy_assistant.py --demo
```

## Run the Streamlit app

Start the web interface with:

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal. In the app, you can select the policy date, enter a
question, and view the answer, status, conflict explanation, and policy sources.

## Run the tests

Run all 15 evaluation questions:

```bash
python run_eval.py
```

The expected result is:

```text
Passed 15/15
```

## Project files

- `policy_assistant.py` contains the policy rules and answer logic.
- `app.py` contains the Streamlit user interface.
- `run_eval.py` runs the evaluation questions.
- `eval.json` contains the expected answers and citations.
- `data/ai-2-data/` contains the policy documents.
- `DECISIONS.md` explains important decisions made while reading the policies.
- `WHERE_IT_BREAKS.md` explains cases where the assistant may not give a reliable answer.
- `AI_USAGE.md` explains how AI help was used during the project.

## What the assistant does well

- Uses the policy date when applying amendments.
- Calculates MDR and GST using exact decimal arithmetic.
- Shows the policy document and clause used for an answer.
- Explains conflicts between the old policy, amendments, and FAQ.
- Returns `CANNOT_ANSWER` when the documents do not cover a question.

## Known limitations

- The question understanding uses simple rules and keywords.
- The assistant does not remember previous questions.
- It cannot calculate an exact settlement date because no bank holiday calendar is included.
- Policy clauses are built into the code; new documents are not loaded automatically.

More details are available in `WHERE_IT_BREAKS.md`.

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

# Start the Streamlit UI
streamlit run app.py
```

Programmatic use:

```python
from policy_assistant import ask
r = ask("Same merchant, a Rs.1,50,000 payment.", "2026-08-15")


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
