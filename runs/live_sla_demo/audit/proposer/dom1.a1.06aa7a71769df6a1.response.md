<notes>
- **What the base run did:** base1 ignored the harness's naive `scripts/calc_sla.py` and hand-computed the answer. It got the right result: INITECH_DE 125 min, $4000 credit, $3700 remaining, $4000 net; UMBRELLA_US 75 min, $600 credit, $500 remaining, $5400 net. The harness was a liability, because the system prompt said "run `scripts/calc_sla.py` quickly and finish". That script uses UTC month boundaries, parses the log as plain CSV, never deduplicates incidents, and ignores PRE_CREDIT and each contract's tier table. Following it would give wrong minutes for both customers.
- **System prompt:** I replaced the "fast assistant, run the script" line with an auditor framing. It adds a trigger line that loads the `sla-reconcile` skill.
- **Script:** I deleted the naive `scripts/calc_sla.py`.
- **New skill `skills/sla-reconcile/SKILL.md`:** it holds the practitioner rules the base run applied correctly by hand, written so they can be checked.
  - The month window is set in the contract timezone, and incidents are classified by local start time.
  - Only OUTAGE status counts.
  - Deduplicate by incident_id and keep the RESOLVED record.
  - Tiers come from each customer's own contract.
  - `remaining_credit_due` is the credit minus the PRE_CREDIT.
  - `net_final_invoice` is the base fee minus the credit only, and the PRE_CREDIT caveat goes in the reply, not the JSON.
- **New skill helper `skills/sla-reconcile/scripts/sla_check.py`:**
  - It reads contracts, incidents and ledger from the working directory, converts each start time to the contract timezone, and prints a per-incident COUNT/skip table.
  - It writes `audit_result.json`.
  - Tier tables are parsed from `contracts.md`.
  - If tzdata is missing (as on this machine), it falls back to the fixed UTC offset stated in the contract.
- **Check:** I ran the script against `context/source`. It reproduced base1's numbers exactly. I did not put the matter's facts into the harness.
</notes>