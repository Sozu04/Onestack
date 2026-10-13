# AI_USAGE.md

AI tools were used (OpenCode / coding assistant) to draft and iterate on this solution.
All generated code was reviewed, corrected and tested by the author. In particular, corrections
made after initial generation include:

- Fixed MDR amount parsing to pick the transaction amount rather than the "Rs.10 lakh" threshold.
- Fixed date-dependent refund answer for the 01 Sep 2026 deletion of clause 3.3.
- Added out-of-scope handling returning CANNOT_ANSWER.
- Verified arithmetic with Decimal and all 15 eval cases pass.
