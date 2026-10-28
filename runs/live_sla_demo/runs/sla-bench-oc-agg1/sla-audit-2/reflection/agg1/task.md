Reconcile the July 2026 SLA downtime credits for all customers in `contracts.md`, `incidents.log`, and `ledger_adjustments.csv`.

Write the final result to `audit_result.json` with this exact JSON schema:
```json
{
  "customers": {
    "<CUSTOMER_ID>": {
      "valid_downtime_min": <int>,
      "total_sla_credit_usd": <float>,
      "remaining_credit_due_usd": <float>,
      "net_final_invoice_usd": <float>
    }
  }
}
```
Definitions:
- `valid_downtime_min`: Sum of valid unplanned outage minutes falling within July 2026 in the customer's contract billing timezone, after deduplicating repeated incident IDs.
- `total_sla_credit_usd`: Full SLA credit earned for July 2026 based on the contract tier.
- `remaining_credit_due_usd`: Additional credit still owed to the customer after subtracting any `PRE_CREDIT` already applied in `ledger_adjustments.csv`.
- `net_final_invoice_usd`: Final invoice amount (`INVOICE` base fee minus `total_sla_credit_usd`).
