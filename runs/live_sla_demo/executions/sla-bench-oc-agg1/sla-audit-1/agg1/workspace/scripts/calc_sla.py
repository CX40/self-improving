"""SLA reconciliation helper. Usage: python scripts/calc_sla.py [dir] -> writes dir/audit_result.json
Reads contracts.md (fee, timezone, tiers), incidents.log, ledger_adjustments.csv.
Prints a per-incident trace to stderr; exits non-zero if any customer cannot be parsed."""
import csv, json, re, sys, os
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

d = sys.argv[1] if len(sys.argv) > 1 else "."
P = lambda f: os.path.join(d, f)
text = open(P("contracts.md"), encoding="utf-8").read()
cust = {}
for blk in re.split(r"^## Customer:\s*", text, flags=re.M)[1:]:
    cid = blk.split()[0]
    fee = float(re.search(r"Monthly Base Fee:\s*\$([\d,\.]+)", blk).group(1).replace(",", ""))
    tzm = re.search(r"Billing Timezone:\s*\**\s*([A-Za-z_]+/[A-Za-z_]+)\s*\(UTC([+-]\d+)", blk)
    tiers = []  # (min_minutes, pct)
    for ln in blk.splitlines():
        m = re.search(r"<\s*(\d+) minutes?:\s*(\d+)%", ln)
        if m: tiers.append((0, int(m.group(2))))
        m = re.search(r"(\d+) to (\d+) minutes?:\s*(\d+)%", ln)
        if m: tiers.append((int(m.group(1)), int(m.group(3))))
        m = re.search(r">=\s*(\d+) minutes?:\s*(\d+)%", ln)
        if m: tiers.append((int(m.group(1)), int(m.group(2))))
    zone, off = tzm.group(1), int(tzm.group(2))
    try:
        tz = ZoneInfo(zone)
    except Exception:
        tz = timezone(timedelta(hours=off))
    cust[cid] = dict(fee=fee, tz=tz, tiers=tiers, mins=0)

inc = {}
for r in csv.DictReader(open(P("incidents.log"), encoding="utf-8")):
    k = (r["incident_id"])
    # dedupe: prefer the RESOLVED/final record; otherwise the last one seen
    final = "RESOLVED" in r["notes"].upper() and "SUPERSEDED" not in r["notes"].upper()
    if k not in inc or final or "RESOLVED" not in inc[k]["notes"].upper():
        inc[k] = r
for k, r in inc.items():
    c = cust[r["customer"]]
    loc = datetime.strptime(r["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(c["tz"])
    ok = r["status"] == "OUTAGE" and (loc.year, loc.month) == (2026, 7)
    print(k, r["customer"], r["status"], r["duration_min"], loc.isoformat(), "COUNT" if ok else "skip", file=sys.stderr)
    if ok: c["mins"] += int(r["duration_min"])

inv, pre = {}, {}
for r in csv.DictReader(open(P("ledger_adjustments.csv"), encoding="utf-8")):
    a = float(r["amount_usd"])
    if r["type"] == "INVOICE": inv[r["customer"]] = a
    elif r["type"] == "PRE_CREDIT": pre[r["customer"]] = pre.get(r["customer"], 0) + abs(a)

out = {"customers": {}}
for cid, c in cust.items():
    pct = max([p for m, p in c["tiers"] if c["mins"] >= m] or [0]) if c["tiers"] else None
    if pct is None: sys.exit("no tiers parsed for " + cid)
    base = inv.get(cid, c["fee"])
    tot = round(c["fee"] * pct / 100, 2)
    out["customers"][cid] = {
        "valid_downtime_min": c["mins"],
        "total_sla_credit_usd": tot,
        "remaining_credit_due_usd": round(max(tot - pre.get(cid, 0), 0), 2),
        "net_final_invoice_usd": round(base - tot, 2),
    }
json.dump(out, open(P("audit_result.json"), "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=2))
