# DECISIONS.md

## Ambiguities encountered and choices made

1. **Conflicting settlement rule (master 1.1 vs circular A).**
   Circular A replaces 1.1 effective 01 Aug 2026: T+0 only with an active "Instant Settlement"
   add-on, otherwise T+1. I treated the circular as authoritative for dates on/after 01 Aug 2026 and
   the original master for earlier dates. Status marked CONFLICT_RESOLVED with the resolution noted.

2. **MDR small-merchant rate (master 2.1 0.30% vs circular B 0.25%).**
   Circular B effective 01 Aug 2026 replaces 2.1. For as_of_date < 01 Aug 2026 I use 0.30%;
   otherwise 0.25%.

3. **MDR cap (master 2.3 ₹15 flat vs circular C split).**
   From 01 Aug 2026 the ₹15 cap applies only to small merchants (≤ ₹10 lakh/month) and ₹25 to
   large merchants. Before that date the single ₹15 cap from master 2.3 stands.

4. **GST on MDR (clause 2.4).**
   GST 18% is applied on the *capped* MDR amount and is stated to be outside the cap. Both
   the fee and GST are computed deterministically with Decimal.

5. **Refund reversal (clause 3.3 deleted).**
   Circular D deletes 3.3 effective 01 Sep 2026. Before that date refunds within 24 hours reverse
   MDR in full; on/after that date 3.2 applies with no exception. The 24-hour check is based
   on the stated timeframe in the question (defaulting to "within 24h" if unspecified).

6. **Daily limit wording (clause 4.3 amended by E).**
   From 01 Aug 2026 the daily limit is ₹1,00,000 *or* the customer's bank limit, whichever is
   lower. For "pay twice" I answer against the stricter aggregate rule.

7. **Per-transaction limit vs. daily limit.**
   A ₹1,50,000 payment is separately checked against the per-transaction limit (₹1,00,000, or
   ₹2,00,000 only for Capital Markets/Insurance with enhanced KYC per 4.2/4.4) and flagged
   when it may not be accepted.

8. **FAQ is stale, not authoritative.**
   The FAQ (Mar 2026) contradicts the policy on the MDR cap and settlement timing. I always
   prefer the Master Policy + amendments and label the FAQ as stale in CONFLICT_RESOLVED answers.

9. **Enhanced limit scope.**
   The ₹2,00,000 limit applies only to Capital Markets/Insurance merchants with enhanced KYC
   (Annexure C), per clauses 4.2/4.4, not to everyone.

10. **Citations format.**
    Circular amendments are cited as `circular_2026_08_amendment.md (clause A)` etc. The FAQ
    has no clause numbers, so it is cited as `merchant_faq_2026-03.md (clause n/a)`.

11. **Merchant size inference for "Same merchant".**
    Q3 is stateless but refers to Q2's large merchant; I treat "Same merchant" as large unless
    explicitly stated otherwise, and document this limitation.

12. **Out-of-scope questions.**
    Anything not covered by the documents returns CANNOT_ANSWER with no citations rather than
    a guess.
