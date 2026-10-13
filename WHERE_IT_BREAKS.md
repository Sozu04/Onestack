# WHERE_IT_BREAKS.md

Three questions the system gets wrong or should not be trusted with, and why.

1. **"What is the MDR for my shop? I do about 8 lakh a month."**
   Partial handling: the size keywords map to "small", but the exact boundary "up to ₹10 lakh"
   is not computed from a numeric volume; any paraphrase of the threshold can misclassify.

2. **Multi-turn references such as "Same merchant as before, but now ₹50,000".**
   The assistant is stateless per call. It assumes "same merchant" means large (to preserve the
   documented Q2→Q3 flow), which is wrong if the prior merchant was small. Passing an explicit
   size is required for a trustworthy answer.

3. **Exact settlement date / working-day arithmetic.**
   The policy says T+1/T+2 excluding Sundays and bank holidays, but no holiday calendar is
   loaded, so the assistant never returns an absolute date like "Monday 18 Aug 2026". It only
   returns the relative rule. Bank-holiday-aware settlement dates are out of scope.
