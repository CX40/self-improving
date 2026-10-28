# SLA & Billing Contracts (Q3-2026)

## Customer: ACME_CORP (Plan: Enterprise-SLA)
- Monthly Base Fee: $12,000.00
- Billing Timezone: **Europe/Berlin (UTC+2 in Summer / CEST)** — All contract month boundaries are evaluated in Customer Local Time!
- SLA Downtime Credit Rule:
  - Only **UNPLANNED** outages (`status=OUTAGE`) in the target billing month (July 2026 in Customer Local Time) count toward SLA downtime.
  - Scheduled maintenance (`status=MAINTENANCE`) or degraded performance (`status=DEGRADED`) do NOT count.
  - If total valid unplanned downtime in July 2026 is:
    - < 30 minutes: 0% credit
    - 30 to 59 minutes: 10% of Monthly Base Fee ($1,200.00)
    - 60 to 119 minutes: 25% of Monthly Base Fee ($3,000.00)
    - >= 120 minutes: 50% of Monthly Base Fee ($6,000.00)

## Customer: GLOBEX_INC (Plan: Growth-SLA)
- Monthly Base Fee: $4,500.00
- Billing Timezone: **America/New_York (UTC-4 in Summer / EDT)** — All contract month boundaries are evaluated in Customer Local Time!
- SLA Downtime Credit Rule:
  - Only **UNPLANNED** outages (`status=OUTAGE`) in the target billing month (July 2026 in Customer Local Time) count toward SLA downtime.
  - Duplicate incident IDs in logs must be deduplicated (keep the final `RESOLVED` record for that `incident_id`).
  - If total valid unplanned downtime in July 2026 is:
    - < 45 minutes: 0% credit
    - 45 to 89 minutes: 10% of Monthly Base Fee ($450.00)
    - >= 90 minutes: 20% of Monthly Base Fee ($900.00)
