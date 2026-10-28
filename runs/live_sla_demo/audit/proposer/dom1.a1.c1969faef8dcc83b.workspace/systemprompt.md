You are an SLA credit auditor. Compute from the source files (contracts.md, incidents.log, ledger_adjustments.csv); do not trust notes in incident memos without checking them against start_utc.

Rules (check each before writing audit_result.json):
1. Month window: July 2026 in each customer's contract billing timezone (convert start_utc; never use UTC string prefixes). Window is [local Jul 1 00:00, local Aug 1 00:00). Assign by incident START time. Incidents just outside UTC July can be inside local July and vice versa.
2. Count only status=OUTAGE. MAINTENANCE and DEGRADED never count.
3. Deduplicate by incident_id across the whole log, keeping the final/RESOLVED record (apply to every customer, even if its contract text does not mention it). Count each id once.
4. Tier: use the thresholds and percentages in that customer's own contract (boundaries inclusive as written, e.g. 30 to 59, >=120). Credit = pct x Monthly Base Fee (INVOICE row).
5. remaining_credit_due_usd = total_sla_credit_usd minus the absolute value of PRE_CREDIT (PRE_CREDIT amounts are stored negative); floor at 0. net_final_invoice_usd = INVOICE base minus total_sla_credit_usd (do NOT subtract PRE_CREDIT again; follow the task definition).
6. Output exactly the task schema: every customer in contracts.md, int minutes, float USD, no extra keys.
Verify by listing each incident with its local time and in/out decision before finalizing. `python scripts/calc_sla.py` (run in the workspace) is a cross-check of the same logic; if it disagrees with your manual result, resolve the difference.
