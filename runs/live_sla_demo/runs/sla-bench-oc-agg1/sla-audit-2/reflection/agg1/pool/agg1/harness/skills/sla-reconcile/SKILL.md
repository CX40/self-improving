---
name: sla-reconcile
description: Rules and checker script for monthly SLA downtime credit reconciliation (contract timezone month boundaries, incident dedup, tiered credit, PRE_CREDIT netting).
---
# SLA credit reconciliation
Inputs: `contracts.md` (base fee, billing timezone, tier table per customer), `incidents.log` (CSV, start_utc, duration_min, status), `ledger_adjustments.csv` (INVOICE, PRE_CREDIT negative amounts).

Rules (apply per customer, each from its own contract text):
1. Month window = the target month in the CONTRACT timezone (convert start_utc to local; use zoneinfo/DST offset stated in contract). Classify by local START time only; do not clip durations. Incidents starting in UTC June/August can be local July and vice versa. Note: the contract's "(UTC+2)" annotation is the summer offset.
2. Count only status=OUTAGE. MAINTENANCE and DEGRADED never count.
3. Dedupe by incident_id: keep one record; prefer the one whose notes say RESOLVED/confirmed, else the last. Count its duration once (apply even if a contract doesn't mention dedup).
4. Credit = tier % x base fee, tier read from that customer's contract (thresholds differ per customer; boundaries inclusive as written, e.g. 30-59, >=120).
5. remaining_credit_due = total_credit - abs(sum PRE_CREDIT) (floor at 0 only if contract says so).
6. net_final_invoice = INVOICE base - total_credit exactly as the task defines it (do NOT also subtract PRE_CREDIT). Mention that caveat in the reply, not in the JSON.
7. Output exactly the task's JSON schema: valid_downtime_min int, others float, every customer in contracts.

Run `python skills/sla-reconcile/scripts/sla_check.py` from the workspace (reads the three files in cwd, prints per-incident classification and writes audit_result.json). Its tier tables are parsed from contracts.md; verify the printed incident table against the raw log by eye before finishing, and confirm that the file contains each customer with the four keys.
