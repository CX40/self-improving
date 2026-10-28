"""SLA audit helper. Usage: python scripts/calc_sla.py [dir] [YYYY-MM]
Reads contracts.md, incidents.log, ledger_adjustments.csv from dir (default .),
writes audit_result.json there, and prints per-incident decisions to stderr.
Exits non-zero if a customer has no parsable timezone, fee or tiers."""
import csv, json, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

d = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
ym = sys.argv[2] if len(sys.argv) > 2 else "2026-07"
Y, M = map(int, ym.split("-"))

def tz_for(name, text):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        m = re.search(r"UTC([+-]\d+)", text)
        if not m:
            sys.exit(f"no tz data for {name}")
        return timezone(timedelta(hours=int(m.group(1))))

contracts = {}
for blk in re.split(r"^## Customer:\s*", (d / "contracts.md").read_text(encoding="utf-8"), flags=re.M)[1:]:
    cid = blk.split()[0]
    fee = re.search(r"Monthly Base Fee:\s*\$([\d,\.]+)", blk)
    tzl = re.search(r"Billing Timezone:\s*\**\s*([A-Za-z_]+/[A-Za-z_]+)([^\n]*)", blk)
    tiers = []
    for ln in blk.splitlines():
        m = re.match(r"\s*-\s*(?:(<)\s*(\d+)|(>=)\s*(\d+)|(\d+)\s*to\s*(\d+))\s*minutes:\s*(\d+)%", ln)
        if m:
            lo = 0 if m.group(1) else int(m.group(4) or m.group(5))
            tiers.append((lo, int(m.group(7))))
    if not (fee and tzl and tiers):
        sys.exit(f"cannot parse contract for {cid}")
    contracts[cid] = dict(fee=float(fee.group(1).replace(",", "")), tz=tz_for(tzl.group(1), tzl.group(2)), tiers=sorted(tiers))

# dedupe by incident_id: prefer the record whose notes say RESOLVED, else the last one
best = {}
for r in csv.DictReader(open(d / "incidents.log", encoding="utf-8")):
    k = r["incident_id"]
    if k not in best or "RESOLVED" in r["notes"].upper() or "RESOLVED" not in best[k]["notes"].upper():
        best[k] = r

mins = {c: 0 for c in contracts}
for r in best.values():
    c = r["customer"]
    if c not in contracts:
        print("UNKNOWN CUSTOMER", r, file=sys.stderr); continue
    loc = datetime.fromisoformat(r["start_utc"].replace("Z", "+00:00")).astimezone(contracts[c]["tz"])
    ok = r["status"].strip() == "OUTAGE" and (loc.year, loc.month) == (Y, M)
    print(f"{r['incident_id']} {c} local={loc:%Y-%m-%d %H:%M} {r['status']} {r['duration_min']}m -> {'COUNT' if ok else 'skip'}", file=sys.stderr)
    if ok:
        mins[c] += int(r["duration_min"])

inv, pre = {}, {}
for r in csv.DictReader(open(d / "ledger_adjustments.csv", encoding="utf-8")):
    a = float(r["amount_usd"]); c = r["customer"]
    if r["type"] == "INVOICE": inv[c] = inv.get(c, 0) + a
    elif r["type"] == "PRE_CREDIT": pre[c] = pre.get(c, 0) + abs(a)

out = {"customers": {}}
for c, k in contracts.items():
    base = inv.get(c, k["fee"])
    pct = 0
    for lo, p in k["tiers"]:
        if mins[c] >= lo: pct = p
    cred = round(base * pct / 100, 2)
    out["customers"][c] = {
        "valid_downtime_min": mins[c],
        "total_sla_credit_usd": cred,
        "remaining_credit_due_usd": round(max(0.0, cred - pre.get(c, 0)), 2),
        "net_final_invoice_usd": round(base - cred, 2),
    }
(d / "audit_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
