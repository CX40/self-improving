"""SLA cross-check: parses contracts.md, incidents.log, ledger_adjustments.csv in cwd."""
import csv, json, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

Y, M = 2026, 7
txt = open("contracts.md", encoding="utf-8").read()
contracts = {}
for blk in re.split(r"(?m)^## Customer: ", txt)[1:]:
    cid = blk.split()[0]
    tz = re.search(r"Billing Timezone: \*\*([A-Za-z_]+/[A-Za-z_]+)", blk).group(1)
    tiers = []  # (min_minutes, pct) from lines like "30 to 59 minutes: 10%", "< 30: 0%", ">= 120: 50%"
    for line in blk.splitlines():
        m = re.match(r"\s*-\s*(<|>=)?\s*(\d+)(?: to (\d+))? minutes: (\d+)%", line)
        if m:
            op, lo, _hi, pct = m.groups()
            tiers.append((0 if op == "<" else int(lo), int(pct) / 100))
    contracts[cid] = {"tz": ZoneInfo(tz), "tiers": sorted(tiers)}

adj = list(csv.DictReader(open("ledger_adjustments.csv", encoding="utf-8")))
base, pre = {}, {}
for r in adj:
    v = float(r["amount_usd"])
    if r["type"] == "INVOICE": base[r["customer"]] = base.get(r["customer"], 0) + v
    elif r["type"] == "PRE_CREDIT": pre[r["customer"]] = pre.get(r["customer"], 0) + abs(v)

final = {}
for r in csv.DictReader(open("incidents.log", encoding="utf-8")):
    prev = final.get(r["incident_id"])
    if prev is None or "RESOLVED" in r["notes"].upper() or "SUPERSEDED" in prev["notes"].upper():
        final[r["incident_id"]] = r  # keep RESOLVED/final record

mins = {c: 0 for c in contracts}
for r in final.values():
    c = r["customer"]
    if c not in contracts or r["status"] != "OUTAGE": continue
    loc = datetime.strptime(r["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(contracts[c]["tz"])
    ok = (loc.year, loc.month) == (Y, M)
    print(r["incident_id"], c, loc.isoformat(), r["duration_min"], "IN" if ok else "OUT")
    if ok: mins[c] += int(r["duration_min"])

out = {"customers": {}}
for c, d in contracts.items():
    pct = 0.0
    for lo, p in d["tiers"]:
        if mins[c] >= lo: pct = p
    cred = round(base[c] * pct, 2)
    out["customers"][c] = {
        "valid_downtime_min": mins[c],
        "total_sla_credit_usd": cred,
        "remaining_credit_due_usd": round(max(cred - pre.get(c, 0), 0), 2),
        "net_final_invoice_usd": round(base[c] - cred, 2),
    }
json.dump(out, open("audit_result.json", "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=2))
