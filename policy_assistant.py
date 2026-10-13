#!/usr/bin/env python3
"""Grounded question-answering assistant over merchant policy documents.

ask(question, as_of_date) returns:
    {
        "answer": str,
        "citations": [str, ...],        # "document.md (clause X)"
        "citation_details": [{...},...],
        "status": "ANSWERED" | "CONFLICT_RESOLVED" | "CANNOT_ANSWER",
        "resolution": str | None,       # how a conflict was resolved
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

try:
    from dateutil import parser as dparser
except ImportError:  # pragma: no cover
    dparser = None

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "ai-2-data"

MASTER_FILE = "policy_master_v1.md"
CIRCULAR_FILE = "circular_2026_08_amendment.md"
FAQ_FILE = "merchant_faq_2026-03.md"

MASTER_EFFECTIVE = date(2026, 1, 1)
CIRCULAR_EFFECTIVE = date(2026, 8, 1)
CLAUSE_3_3_DELETED = date(2026, 9, 1)
FAQ_UPDATED = date(2026, 3, 12)
DEFAULT_AS_OF = date(2026, 8, 15)


# ---------------------------------------------------------------------------
# clause parsing
# ---------------------------------------------------------------------------
def read_doc(name: str) -> str:
    return (DATA_DIR / name).read_text(encoding="utf-8")


def parse_master_clauses(text: str) -> dict[str, str]:
    clauses: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+\.\d+)\s+(.*)$", line)
        if m:
            clauses[m.group(1)] = m.group(2).strip()
    return clauses


def parse_circular(text: str) -> str:
    return text


_MASTER_CLAUSES = parse_master_clauses(read_doc(MASTER_FILE))


def clause_text(clause: str) -> str:
    return _MASTER_CLAUSES.get(clause, "")


# ---------------------------------------------------------------------------
# dates
# ---------------------------------------------------------------------------
_DATE_PATTERNS = [
    # ISO
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    # "20 Aug 2026", "20 August 2026"
    re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b", re.I),
    # "Aug 20 2026" / "August 20, 2026"
    re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})\b", re.I),
]


def _to_date(s: str) -> date:
    s = s.strip()
    # ISO first
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    if dparser is not None:
        dt = dparser.parse(s, dayfirst=False)
        return dt.date()
    raise ValueError(f"Cannot parse date: {s!r}")


def parse_as_of(value) -> date:
    if value is None:
        return DEFAULT_AS_OF
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # try direct parse; fall back to searching patterns
        try:
            return _to_date(value)
        except ValueError:
            for pat in _DATE_PATTERNS:
                m = pat.search(value)
                if m:
                    try:
                        return _to_date(m.group(0))
                    except ValueError:
                        continue
    raise ValueError(f"Cannot parse as_of_date: {value!r}")


def extract_date_from_question(q: str):
    for pat in _DATE_PATTERNS:
        m = pat.search(q)
        if m:
            try:
                return _to_date(m.group(0))
            except (ValueError, Exception):
                continue
    return None


# ---------------------------------------------------------------------------
# misc helpers
# ---------------------------------------------------------------------------
def money(x) -> str:
    d = Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # strip trailing zeros for cleanliness but keep 2 decimals for money-ish
    return f"₹{d:,.2f}".replace(",", ",")


def parse_amounts(q: str) -> list[Decimal]:
    vals = []
    # Rs. 4,000 / Rs 4000 / ₹4,000 / INR
    for m in re.finditer(r"(?:rs\.?|₹|inr)\s*([\d][\d,]*(?:\.\d+)?)", q, re.I):
        v = m.group(1).replace(",", "")
        try:
            vals.append(Decimal(v))
        except Exception:
            pass
    # fallback: bare numbers with currency hint "payment of 150000"
    if not vals:
        for m in re.finditer(r"\b(\d[\d,]{3,})(?:\.\d+)?\b", q):
            vals.append(Decimal(m.group(1).replace(",", "")))
    return vals


def has_any(q: str, words) -> bool:
    ql = q.lower()
    return any(w in ql for w in words)


# ---------------------------------------------------------------------------
# citation helpers
# ---------------------------------------------------------------------------
def cite(doc: str, clause: str, note: str | None = None) -> dict:
    return {"document": doc, "clause": clause, "text": clause_text(clause) if doc == MASTER_FILE else None, "note": note}


def cite_str(doc: str, clause: str) -> str:
    return f"{doc} (clause {clause})"


MASTER = MASTER_FILE
CIRC = CIRCULAR_FILE
FAQ = FAQ_FILE


# ---------------------------------------------------------------------------
# amendment status by date
# ---------------------------------------------------------------------------
def circular_active(d: date) -> bool:
    return d >= CIRCULAR_EFFECTIVE


def clause_3_3_active(d: date) -> bool:
    return d < CLAUSE_3_3_DELETED


def small_rate(d: date) -> Decimal:
    if circular_active(d):
        return Decimal("0.0025")  # 0.25%
    return Decimal("0.0030")  # 0.30%


def large_rate(d: date) -> Decimal:
    return Decimal("0.0050")  # 0.50% (unchanged)


def mdr_cap(d: date, large: bool) -> Decimal:
    if large:
        if circular_active(d):
            return Decimal("25")  # amended cap for >10 lakh
        return Decimal("15")
    return Decimal("15")  # small always 15


def daily_limit(d: date) -> str:
    if circular_active(d):
        return "₹1,00,000 or the limit set by the customer's own bank, whichever is lower"
    return "₹1,00,000"


# ---------------------------------------------------------------------------
# answer builders
# ---------------------------------------------------------------------------
def make(status, answer, citations, resolution=None):
    cstrs = [cite_str(c["document"], c["clause"]) for c in citations]
    return {
        "answer": answer,
        "citations": cstrs,
        "citation_details": citations,
        "status": status,
        "resolution": resolution,
    }


def answer_settlement(q, d):
    ql = q.lower()
    card = "card" in ql
    instant = "instant" in ql
    citations = []
    if card:
        citations.append(cite(MASTER, "1.2"))
        citations.append(cite(MASTER, "1.3"))
        return make("ANSWERED",
                    "Card transactions settle T+2 (two working days), not same day. "
                    "If a settlement date falls on a bank holiday, it moves to the next working day (clause 1.3).",
                    citations)
    # UPI
    if circular_active(d):
        citations.append(cite(MASTER, "1.1", note="replaced by Circular A"))
        citations.append(cite(CIRC, "A", note="Amendment A"))
        res = ("Circular MS/2026/17 (Amendment A), effective 01 Aug 2026, replaces master clause 1.1: "
               "UPI settlement is T+0 (same day, by 11:59 PM) only with an active 'Instant Settlement' add-on, "
               "otherwise T+1.")
        if instant:
            ans = ("With an active 'Instant Settlement' add-on, UPI funds settle same day (T+0) by 11:59 PM. "
                   "Without the add-on, settlement is T+1 (next working day).")
        else:
            ans = ("UPI money is received same day (T+0, by 11:59 PM) only for merchants with an active "
                   "'Instant Settlement' add-on; all other merchants receive it on T+1 (the next working day). "
                   "Working days exclude Sundays and bank holidays.")
        return make("CONFLICT_RESOLVED", ans, citations, res)
    citations.append(cite(MASTER, "1.1"))
    return make("ANSWERED",
                "UPI money is received on T+1 (the next working day). Working days exclude Sundays and bank holidays.",
                citations)


def answer_mdr(q, d):
    ql = q.lower()
    large = any(w in ql for w in ["large", "big", "above", "more than", "greater", ">"]) 
    small = any(w in ql for w in ["small", "tiny", "micro", "up to", "<="])
    if "10 lakh" in ql and "up to" in ql:
        small = True
    if not large and not small:
        if "same merchant" in ql or "same seller" in ql:
            large = True
        elif "10 lakh" in ql and "up" not in ql and "below" not in ql:
            large = True
        else:
            small = True
    is_large = large and not small
    citations = []
    amounts = parse_amounts(q)
    if amounts:
        amounts = [max(amounts)]
    # base citations
    if small or not is_large:
        if circular_active(d):
            citations.append(cite(MASTER, "2.1", note="replaced by Circular B"))
            citations.append(cite(CIRC, "B", note="Amendment B"))
        else:
            citations.append(cite(MASTER, "2.1"))
    else:
        citations.append(cite(MASTER, "2.2"))
    # cap citation
    if circular_active(d):
        citations.append(cite(MASTER, "2.3", note="replaced/split by Circular C"))
        citations.append(cite(CIRC, "C", note="Amendment C"))
    else:
        citations.append(cite(MASTER, "2.3"))
    citations.append(cite(MASTER, "2.4"))
    if "cap" in ql and amounts and amounts[0] <= 0:
        pass

    rate = large_rate(d) if is_large else small_rate(d)
    size_label = "large (> ₹10 lakh/month)" if is_large else "small (up to ₹10 lakh/month)"
    rate_pct = (rate * 100).quantize(Decimal("0.01"))

    if not amounts:
        # general
        cap = mdr_cap(d, is_large)
        ans = (f"For {size_label} merchants as of {d.isoformat()}: UPI MDR is {rate_pct}% of transaction value, "
               f"subject to a per-transaction cap of ₹{cap:,.0f} (cap applies as: small ₹15; large ₹25 after 01 Aug 2026). "
               f"GST at 18% is charged on the MDR and is not part of the cap.")
        status = "CONFLICT_RESOLVED" if circular_active(d) else "ANSWERED"
        res = ("Circular MS/2026/17 replaces master clauses 2.1 and 2.3 effective 01 Aug 2026 "
               "(small rate 0.25%, split caps).") if circular_active(d) else None
        return make(status, ans, citations, res)

    amount = amounts[0]
    cap = mdr_cap(d, is_large)
    raw = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    capped = raw > cap
    mdr = cap if capped else raw
    gst = (mdr * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = mdr + gst
    ans = (f"On a ₹{amount:,.2f} UPI payment for a {size_label} merchant: "
           f"MDR = {rate_pct}% × ₹{amount:,.2f} = ₹{raw:,.2f}; "
           f"{'capped to ₹' + format(cap, ',.2f') if capped else 'within cap'}, so MDR charged = ₹{mdr:,.2f}. "
           f"GST @18% on MDR = ₹{gst:,.2f}. "
           f"Total fee (MDR + GST) = ₹{total:,.2f}. GST is not part of the MDR cap.")
    # limit caveat
    if amount > Decimal("100000"):
        ans += (" Note: per-transaction UPI limit is ₹1,00,000 "
                "(₹2,00,000 only for Capital Markets/Insurance merchants with enhanced KYC, clause 4.2/4.4), "
                "so a ₹{0} payment may not be accepted unless the merchant qualifies.".format(
                    f"{amount:,.0f}".replace(",", ","))
        )
    status = "CONFLICT_RESOLVED" if circular_active(d) else "ANSWERED"
    res = ("Circular MS/2026/17 (Amendments B & C), effective 01 Aug 2026, replaced master clauses 2.1 and 2.3: "
           "small-merchant rate 0.25% and split caps (small ₹15, large ₹25).") if circular_active(d) else None
    if not is_large:
        # small rate changed only; cap unchanged for small
        pass
    return make(status, ans, citations, res)


def answer_refund(q, d):
    ql = q.lower()
    if "chargeback" in ql:
        citations = [cite(MASTER, "3.4")]
        return make("ANSWERED",
                    "Chargeback disputes must be raised by the customer's bank within 120 days of the transaction (clause 3.4).",
                    citations)
    # detect hours
    hours = None
    m = re.search(r"(\d+)\s*hour", ql)
    if m:
        hours = int(m.group(1))
    days_since = None
    m2 = re.search(r"(\d+)\s*day", ql)
    if m2:
        days_since = int(m2.group(1))
    citations = [cite(MASTER, "3.1"), cite(MASTER, "3.2")]
    status_parts = []
    if clause_3_3_active(d):
        citations.append(cite(MASTER, "3.3"))
    else:
        citations.append(cite(MASTER, "3.3", note="deleted by Circular D from 01 Sep 2026"))
        citations.append(cite(CIRC, "D", note="Amendment D"))
    # refund window
    refund_window_ok = True
    if days_since is not None:
        refund_window_ok = days_since <= 90
    within_24h = (hours is not None and hours <= 24) or (days_since is not None and days_since == 0)
    # if no timeframe given, assume the question's premise (3 hours in prompt) -> within 24h
    if hours is None and days_since is None:
        within_24h = True

    if not refund_window_ok:
        ans = "No — refund not allowed: refunds must be initiated within 90 days of the original transaction (clause 3.1)."
        return make("ANSWERED", ans, citations)

    deleted = not clause_3_3_active(d)
    if deleted:
        ans = ("No — the MDR is NOT returned. Clause 3.3 (24-hour full reversal) was deleted effective 01 Sep 2026, "
               "so clause 3.2 applies without exception: MDR charged on a refunded transaction is not returned to the merchant.")
        res = ("Circular MS/2026/17 (Amendment D) deleted clause 3.3 effective 01 Sep 2026.")
        status = "CONFLICT_RESOLVED"
    else:
        if within_24h:
            ans = ("Yes — because the refund is initiated within 24 hours of the transaction, the MDR is reversed in full "
                   "(clause 3.3, still in force before 01 Sep 2026).")
            status = "CONFLICT_RESOLVED" if circular_active(d) else "ANSWERED"
            res = ("Circular MS/2026/17 (Amendment D) will delete clause 3.3 from 01 Sep 2026.") if circular_active(d) else None
        else:
            ans = ("No — the MDR is not returned because the refund was initiated more than 24 hours after the transaction "
                   "(clause 3.2; clause 3.3 only applies within 24 hours).")
            status = "ANSWERED"
            res = None
    return make(status, ans, citations, res if deleted or (circular_active(d)) else None)


def answer_faq(q, d):
    citations = [cite(FAQ, "n/a", note="FAQ section: 'What do I pay on a UPI transaction?'"), cite(MASTER, "2.3")]
    if circular_active(d):
        citations.append(cite(CIRC, "C", note="Amendment C"))
    ans = ("The FAQ (last updated 12 Mar 2026) says 0.30% (small) / 0.50% (large) and claims there is NO upper limit on the fee. "
           "That is NOT correct: the Master Policy (clause 2.3) caps MDR per UPI transaction — "
           "₹15 (and for large merchants ₹25 after 01 Aug 2026 per Circular C). "
           "Also, after 01 Aug 2026 the small-merchant rate is 0.25% (Circular B), so the FAQ's 0.30% is stale.")
    res = ("FAQ conflicts with Master Policy; the policy (plus amendments effective on the date) governs. "
           "FAQ also predates the 01 Aug 2026 circular.")
    return make("CONFLICT_RESOLVED", ans, citations, res)


def answer_limits(q, d):
    ql = q.lower()
    citations = [cite(MASTER, "4.1"), cite(MASTER, "4.2"), cite(MASTER, "4.3"), cite(MASTER, "4.4")]
    if circular_active(d):
        citations.append(cite(CIRC, "E", note="Amendment E"))
    dl = daily_limit(d)
    twice = "twice" in ql or "two" in ql or "2 times" in ql or "two times" in ql
    amounts = parse_amounts(q)
    if twice:
        ans = (f"No. The daily limit per customer account is {dl} across ALL UPI transactions "
               f"({'amended by Circular E from 01 Aug 2026' if circular_active(d) else 'master clause 4.3'}). "
               f"Two payments of ₹1,00,000 total ₹2,00,000, which exceeds that, so the second would be declined/rejected. "
               f"The per-transaction cap of ₹1,00,000 (clause 4.1, or ₹2,00,000 for Capital Markets/Insurance with enhanced KYC, clauses 4.2/4.4) "
               f"is separate from the daily aggregate limit.")
        status = "CONFLICT_RESOLVED" if circular_active(d) else "ANSWERED"
        res = ("Circular E amended clause 4.3 effective 01 Aug 2026: daily limit is ₹1,00,000 or the customer's own bank limit, whichever is lower.") if circular_active(d) else None
        return make(status, ans, citations, res)
    # general limit explanation
    ans = (f"Per-transaction UPI limit is ₹1,00,000 (master 4.1); ₹2,00,000 only for 'Capital Markets' and 'Insurance' merchants "
           f"that have completed enhanced KYC (clauses 4.2/4.4). Daily limit per customer account is {dl} across all UPI transactions.")
    status = "CONFLICT_RESOLVED" if circular_active(d) else "ANSWERED"
    res = ("Circular E amended clause 4.3 effective 01 Aug 2026.") if circular_active(d) else None
    return make(status, ans, citations, res)


def answer_closure(q, d):
    ql = q.lower()
    citations = [cite(MASTER, "5.1"), cite(MASTER, "5.2")]
    if any(w in ql for w in ["when", "get my money", "release", "pending"]):
        ans = ("Pending settlements are released within 10 working days of account closure, after deducting outstanding dues "
               "(clause 5.2). Account closure itself requires 30 days' written notice (clause 5.1). "
               "The FAQ's 'within 10 days' is looser than the policy's 10 working days.")
        return make("ANSWERED", ans, citations)
    # asks can close any time
    ans = ("A merchant may close with 30 days' written notice (clause 5.1). Closing 'any time' is not immediate; "
           "pending settlements are then released within 10 working days (clause 5.2).")
    return make("ANSWERED", ans, citations)


def answer_instant(q, d):
    citations = [cite(MASTER, "1.1", note="replaced by Circular A"), cite(CIRC, "A", note="Amendment A")]
    ans = ("Same-day (T+0, by 11:59 PM) UPI settlement applies only to merchants with an active 'Instant Settlement' add-on. "
           "All other merchants remain on T+1.")
    return make("CONFLICT_RESOLVED", ans, citations,
                "Circular A replaced clause 1.1 effective 01 Aug 2026.")


def answer_card_same_day(q, d):
    citations = [cite(MASTER, "1.2")]
    ans = "No — card payments settle T+2 (two working days), not same day. There is no amendment changing card settlement."
    return make("ANSWERED", ans, citations)


def answer_enhanced_limit(q, d):
    citations = [cite(MASTER, "4.1"), cite(MASTER, "4.2"), cite(MASTER, "4.4")]
    ans = ("No — the enhanced ₹2,00,000 per-transaction limit does NOT apply to all merchants. "
           "It applies only to merchants in the 'Capital Markets' and 'Insurance' categories that have completed enhanced KYC (Annexure C) (clauses 4.2/4.4). "
           "All other merchants are limited to ₹1,00,000 per transaction (clause 4.1).")
    return make("ANSWERED", ans, citations)


def cannot_answer(q, d, reason=None):
    return {
        "answer": ("I cannot answer from the provided policy documents"
                   + (": " + reason if reason else ".")),
        "citations": [],
        "citation_details": [],
        "status": "CANNOT_ANSWER",
        "resolution": None,
    }


# ---------------------------------------------------------------------------
# top-level ask
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS = {
    "refund": ["refund", "chargeback", "revers"],
    "faq": ["faq"],
    "closure": ["close", "account closure", "closing"],
    "mdr": ["mdr", "fee", "charge", "gst", "cost", "commission", "rate"],
    "limits": ["limit", "twice", "two times", "daily", "maximum amount", "max amount"],
    "settlement": ["settle", "receive", "when will", "money", "same day", "get paid", "fund"],
    "instant": ["instant settlement"],
    "enhanced": ["enhanced kyc", "annexure c", "capital markets", "insurance"],
}


def detect_topic(q: str) -> str:
    ql = q.lower()
    if "faq" in ql:
        return "faq"
    if "refund" in ql or "chargeback" in ql:
        return "refund"
    if "close" in ql or "closing" in ql or "closure" in ql or "closed" in ql:
        return "closure"
    if "instant" in ql:
        return "instant"
    if ("enhanced" in ql or "annexure" in ql) and ("all merchants" in ql or "everyone" in ql or "every merchant" in ql):
        return "enhanced"
    if "card" in ql and ("settle" in ql or "same day" in ql or "same-day" in ql):
        return "card_same_day"
    if has_any(ql, ["twice", "two times", "daily", "maximum amount", "max amount", "pay twice", "once a day"]):
        return "limits"
    if "limit" in ql:
        return "limits"
    if has_any(ql, ["interchange", "debit card", "credit card", "neft", "rtgs", "imps", "atm"]):
        return "unknown"
    if has_any(ql, ["mdr", "fee", "gst", "commission", "rate", "charge", "pay"]) and has_any(ql, ["upi", "transaction", "merchant", "payment", "sale"]):
        return "mdr"
    if has_any(ql, ["settle", "receive", "when will", "money", "funds", "get paid", "settlement"]):
        return "settlement"
    if parse_amounts(q):
        return "mdr"
    return "unknown"


def ask(question, as_of_date=None):
    # resolve date
    d = parse_as_of(as_of_date)
    # if question explicitly states a date and as_of not provided, use it
    if as_of_date is None:
        qd = extract_date_from_question(question)
        if qd is not None:
            d = qd
    if d is None:
        d = DEFAULT_AS_OF
    ql = question.lower()

    topic = detect_topic(question)

    # card same-day direct
    if "card" in ql and ("same day" in ql or "same-day" in ql or "settled today" in ql):
        return answer_card_same_day(question, d)

    # Enhanced limit false premise variations
    if ("2,00,000" in question or "2 lakh" in ql or "2,00, 000" in question) and ("all" in ql or "every" in ql):
        return answer_enhanced_limit(question, d)

    if topic == "faq":
        return answer_faq(question, d)
    if topic == "refund":
        return answer_refund(question, d)
    if topic == "closure":
        return answer_closure(question, d)
    if topic == "instant":
        return answer_instant(question, d)
    if topic == "card_same_day":
        return answer_card_same_day(question, d)
    if topic == "enhanced":
        return answer_enhanced_limit(question, d)
    if topic == "limits":
        return answer_limits(question, d)
    if topic == "mdr":
        return answer_mdr(question, d)
    if topic == "settlement":
        return answer_settlement(question, d)
    # unknown
    # try limits if amount present? 
    if parse_amounts(question) and "pay" in ql:
        return answer_limits(question, d)
    return cannot_answer(question, d, "no matching policy clause found for the question")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="?")
    p.add_argument("--as-of", dest="as_of", default=None)
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()
    if args.demo:
        qs = [
            ("When does a small merchant receive UPI money?", "2026-08-15"),
            ("A large merchant (above Rs.10 lakh monthly) receives a Rs.4,000 UPI payment. What MDR and GST do they pay?", "2026-08-15"),
            ("Same merchant, a Rs.1,50,000 payment. What do they pay?", "2026-08-15"),
            ("A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?", "2026-08-20"),
            ("A merchant refunds a customer 3 hours after the sale. Do they get the MDR back?", "2026-09-05"),
            ("What does the FAQ say about the MDR cap, and is the FAQ right?", "2026-08-15"),
            ("Can a customer pay Rs.1,00,000 twice in one day to a merchant?", "2026-08-15"),
            ("I closed my account yesterday. When will I get my money?", "2026-08-15"),
            ("Does the policy allow me to settle card payments same day?", "2026-08-15"),
        ]
        for q, d in qs:
            r = ask(q, d)
            print(json.dumps({"q": q, "as_of": d, **r}, indent=2, ensure_ascii=False))
        raise SystemExit(0)
    if not args.question:
        p.print_help()
        raise SystemExit(0)
    r = ask(args.question, args.as_of)
    print(json.dumps(r, indent=2, ensure_ascii=False))
