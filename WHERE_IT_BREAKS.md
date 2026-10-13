# WHERE_IT_BREAKS.md

Three questions the system gets wrong or should not be trusted with, and why.
Here are three cases where the system may give a wrong answer or should not be fully trusted:

1. "What is the MDR for my shop? I do about 8 lakh a month."
   The system can understand words like "small", but it does not always calculate the exact monthly
   amount correctly. Because of this, it may choose the wrong merchant category.

2. Multi-turn references such as "Same merchant as before, but now ₹50,000".
   The system does not remember previous questions. If the user says "same merchant", it assumes the
   merchant is large. This may be wrong if the earlier merchant was small. It is better to mention the
   merchant size in every question.

3. Exact settlement date / working-day arithmetic.
   The system can say T+1 or T+2, but it cannot calculate the exact date. It does not have a list of
   bank holidays. So it gives the general settlement rule instead of an exact date.
