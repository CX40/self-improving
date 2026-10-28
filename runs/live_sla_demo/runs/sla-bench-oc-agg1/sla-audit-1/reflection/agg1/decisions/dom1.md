Nothing was run. I couldn't test `calc_sla.py` because neither Bash nor PowerShell has Python. I checked it by reading the code against the source files.

The one base rollout (base1, haiku, 17.6s) produced the correct result for both customers:
- ACME_CORP: 75 min, 3000 total credit, 2500 remaining, 9000 net.
- GLOBEX_INC: 95 min, 900 total credit, 900 remaining, 3600 net.

It got there by reasoning, not by the harness. It never ran `scripts/calc_sla.py`, and the old system prompt ("run the script quickly and finish") would have produced wrong numbers if it had. The script was naive: it used UTC prefixes, ignored the contract timezones, applied no dedup, and set remaining credit equal to total credit. The rollout also hesitated over whether the `PRE_CREDIT` should reduce the invoice.

Changes:
1. **`systemprompt.md` rewritten.** It now states the practitioner rules the rollout applied unaided:
   - Evaluate the month window in the customer's billing timezone, with the incident assigned by its start time.
   - Count only `OUTAGE`.
   - Deduplicate by incident ID, keeping the `RESOLVED` record.
   - Take tier thresholds from each contract.
   - Remaining credit is total minus the absolute value of the (negative) `PRE_CREDIT`.
   - Net invoice is base minus total credit, per the task definition, with no second subtraction.
   - Deliver exactly the task schema.
   - List each incident with its local time and in/out decision before finalizing.
   
   This removes the harmful "fast billing assistant" instruction. I put no matter-specific facts in it, so it stays valid for other months and customers.
2. **`scripts/calc_sla.py` rewritten as a correct, generic cross-check.** It parses the contracts, converts times with `zoneinfo`, deduplicates keeping `RESOLVED`, applies the tiers, and subtracts `PRE_CREDIT` from the credit for the remaining amount. The prompt tells the agent to resolve any disagreement with its manual result.

No skills were added; the logic is short enough to sit in the system prompt.