- **The base harness told the solver to run a naive script.** `systemprompt.md` said to run `scripts/calc_sla.py` "quickly and finish". The old script filtered on UTC strings that start with `2026-07`. It did not dedupe incident IDs. It used hard-coded tiers chosen by fee size. It never subtracted `PRE_CREDIT`. Run as written, it would have given wrong minutes for both customers, such as counting INC-104 and INC-201 and double-counting INC-202. It would also have returned the full credit as "remaining" for ACME.
- **The base1 rollout got the right answer only by ignoring the harness.** The solver read the inputs, never ran the script, and wrote 75 and 95 minutes with correct credits. It also skipped any re-read of the deliverable, and the output of its first `cat` showed `contracts.md` cut off mid-file ("- " after GLOBEX_INC). It got the GLOBEX tiers right anyway, but nothing in the harness told it to re-read a truncated view.
- **Replaced `scripts/calc_sla.py`.** The new version:
  - parses fee, timezone and tiers from `contracts.md`;
  - converts each incident to the contract timezone using `zoneinfo`, with a fixed-offset fallback;
  - dedupes incident IDs, keeping the RESOLVED record;
  - counts only OUTAGE status inside local July;
  - subtracts `PRE_CREDIT` and floors the remainder at 0;
  - prints a per-incident trace;
  - exits with an error if no tiers parse.
  I ran it on the workspace sources. It reproduces base1's values (ACME 75 min, $3,000 credit, $2,500 remaining, $9,000 net; GLOBEX 95 min, $900, $900, $3,600).
- **Rewrote `systemprompt.md`** as a short procedure:
  - read every input in full and re-read if the view looks cut off;
  - run the script and cross-check its trace against the contract text;
  - re-open and validate `audit_result.json`;
  - cap the fallback at one fix attempt.
  This replaces "finish quickly", which led to the naive path.
- **No skills, plugins or subagents added.** A single deterministic script and a few lines of prose are enough for this task.