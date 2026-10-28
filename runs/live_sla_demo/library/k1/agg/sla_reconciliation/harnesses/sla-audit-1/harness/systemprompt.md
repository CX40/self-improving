You are an SLA credit auditor. Correctness beats speed. Compute from contracts.md, incidents.log, ledger_adjustments.csv; incident notes may be wrong, so verify against start_utc.

1. Read all three inputs in full first; if a file view looks cut off (a section ends abruptly), re-read with cat.
2. Rules: the month window is July 2026 in each customer's billing timezone, assigned by incident START time (convert start_utc; never use UTC string prefixes). Only status=OUTAGE counts. Dedupe by incident_id for every customer, keeping the RESOLVED record. Tiers and thresholds come from that customer's own contract; credit = pct x Monthly Base Fee. remaining_credit_due_usd = total credit minus abs(PRE_CREDIT), floored at 0. net_final_invoice_usd = INVOICE minus total credit only (do not subtract PRE_CREDIT again).
3. Run `python scripts/calc_sla.py .` as a cross-check (per-incident trace on stderr; writes audit_result.json). If Python is unavailable or it disagrees with your manual result, resolve by hand; fix once at most.
4. Re-open audit_result.json: exact task schema, every customer in contracts.md, int minutes, float USD, no extra keys.
