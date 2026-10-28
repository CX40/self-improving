"""SLA credit reconciliation: contract-timezone month, dedup, contract tiers, PRE_CREDIT."""
import csv, json, re, sys
from datetime import datetime, timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

YEAR, MONTH = 2026, 7
contracts = open("contracts.md", encoding="utf-8").read()
blocks = re.split(r"^## Customer: ", contracts, flags=re.M)[1:]
cust = {}
for b in blocks:
    cid = b.split()[0]
    tz = re.search(r"Billing Timezone:\W*([A-Za-z_]+/[A-Za-z_]+)", b).group(1)
    tiers = []  # (min_minutes, pct)
    for line in b.splitlines():
        m = re.match(r"\s*- (?:< ?(\d+) minutes: (\d+)%|(\d+) to \d+ minutes: (\d+)%|>= ?(\d+) minutes: (\d+)%)", line)
        if not m:
            continue
        if m.group(1):
            tiers.append((0, int(m.group(2))))
        elif m.group(3):
            tiers.append((int(m.group(3)), int(m.group(4))))
        else:
            tiers.append((int(m.group(5)), int(m.group(6))))
    try:
        z = ZoneInfo(tz)
    except Exception:  # no tzdata: fall back to the summer offset stated in the contract (UTC+2 / UTC-4)
        o = re.search(r"UTC([+-])(\d+)", b)
        z = timezone(timedelta(hours=int(o.group(2)) * (1 if o.group(1) == "+" else -1)))
        print("WARN: tzdata missing, using fixed offset for", cid)
    cust[cid] = {"tz": z, "tiers": sorted(tiers)}

# ledger
base, pre = {}, {}
for r in csv.DictReader(open("ledger_adjustments.csv", encoding="utf-8")):
    a = float(r["amount_usd"])
    if r["type"] == "INVOICE":
        base[r["customer"]] = base.get(r["customer"], 0) + a
    elif r["type"] == "PRE_CREDIT":
        pre[r["customer"]] = pre.get(r["customer"], 0) + abs(a)

# dedup by incident_id: prefer RESOLVED note, else last
chosen = {}
for r in csv.DictReader(open("incidents.log", encoding="utf-8")):
    k = r["incident_id"]
    resolved = "RESOLVED" in r["notes"].upper()
    if k not in chosen or resolved or "RESOLVED" not in chosen[k]["notes"].upper():
        chosen[k] = r

mins = {c: 0 for c in cust}
for k, r in chosen.items():
    c = r["customer"]
    loc = datetime.strptime(r["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(cust[c]["tz"])
    ok = r["status"] == "OUTAGE" and (loc.year, loc.month) == (YEAR, MONTH)
    print(f"{k} {c} local={loc:%Y-%m-%d %H:%M} {r['status']} {r['duration_min']}m -> {'COUNT' if ok else 'skip'}")
    if ok:
        mins[c] += int(r["duration_min"])

out = {"customers": {}}
for c, d in cust.items():
    pct = 0
    for lo, p in d["tiers"]:
        if mins[c] >= lo:
            pct = p
    credit = round(base[c] * pct / 100, 2)
    out["customers"][c] = {
        "valid_downtime_min": mins[c],
        "total_sla_credit_usd": credit,
        "remaining_credit_due_usd": round(credit - pre.get(c, 0), 2),
        "net_final_invoice_usd": round(base[c] - credit, 2),
    }
json.dump(out, open("audit_result.json", "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=2))
