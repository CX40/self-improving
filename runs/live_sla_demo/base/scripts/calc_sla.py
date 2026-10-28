"""Base quick calculator for SLA audit."""
import csv
import json
import sys

# Quick naive calculation from incidents.log
rows = list(csv.DictReader(open("incidents.log", encoding="utf-8")))
adj = list(csv.DictReader(open("ledger_adjustments.csv", encoding="utf-8")))

customers = {}
for r in adj:
    c = r["customer"]
    if r["type"] == "INVOICE":
        customers[c] = {"base": float(r["amount_usd"]), "min": 0}

for r in rows:
    c = r["customer"]
    # Naive check: UTC string starts with 2026-07 and status is OUTAGE
    if r["start_utc"].startswith("2026-07") and r["status"] == "OUTAGE":
        customers[c]["min"] += int(r["duration_min"])

out = {"customers": {}}
for c, d in customers.items():
    mins = d["min"]
    base = d["base"]
    # Naive tier check
    if base >= 8000:
        pct = 0.50 if mins >= 120 else (0.25 if mins >= 60 else (0.10 if mins >= 30 else 0.0))
    else:
        pct = 0.20 if mins >= 90 else (0.10 if mins >= 45 else 0.0)
    cred = round(base * pct, 2)
    out["customers"][c] = {
        "valid_downtime_min": mins,
        "total_sla_credit_usd": cred,
        "remaining_credit_due_usd": cred,
        "net_final_invoice_usd": round(base - cred, 2),
    }

with open("audit_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
