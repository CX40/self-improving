component: systemprompt.md
candidates: inv1
change: Replaced the base line "fast billing assistant, run `python scripts/calc_sla.py` quickly and finish" with a four-step procedure: (1) read all three inputs in full, re-reading with cat if a view looks cut off; (2) run `python scripts/calc_sla.py .` as the primary path, with "do NOT use any other version of this script's logic from memory" and at most one fix attempt; (3) cross-check the script's trace against the log notes and contract text; (4) re-open audit_result.json and check the schema. It does not spell out the domain rules (local-time window, OUTAGE only, dedup, PRE_CREDIT handling, net invoice).
observed: inv1.md is the only run that read each input file separately. Its first Bash chain (`ls && wc -c * && cat ...`) exited 1 because `wc` hit directories, so the `cat` never ran. The solver then used Read on contracts.md, incidents.log and ledger_adjustments.csv. That re-read follows from the failed command, so it is not clear evidence of step 1. The solver never ran calc_sla.py (step 2), never re-opened audit_result.json (step 4), and wrote the JSON by hand right after the Reads. Like base1, its final message hedged on net invoice ("If the invoice should also net out the pre-credit, ACME's figure would be $8,500"). Deliverable is identical to base1 (75/95 min, 3000/900, 2500/900, 9000/3600). It was the slowest run (20.3s against 14–18s).
verdict: no observed effect

component: systemprompt.md
candidates: dom1
change: Replaced the base line with an explicit domain rulebook: window [local Jul 1 00:00, local Aug 1 00:00) by incident START; only OUTAGE counts; dedupe by incident_id for every customer, keeping RESOLVED; per-contract inclusive tiers; remaining = credit − abs(PRE_CREDIT), floored at 0; net = INVOICE − credit, "do NOT subtract PRE_CREDIT again"; exact schema. Adds "verify by listing each incident with its local time and in/out decision", with calc_sla.py as a cross-check.
observed: dom1.md made one `cat` of all inputs (the recorded view of contracts.md cuts off at "60 "), wrote the JSON straight away, and never ran the script. Its summary lists each incident with in/out and the UTC bounds of each local window. base1 and agg1 did the same without this rule, so the listing was not caused by it. It did not hedge on net invoice, which fits the explicit "do NOT subtract PRE_CREDIT again" clause, but that is one rollout and the JSON field was already correct in base1. It said itself that it did not validate the JSON. Deliverable identical to base1.
verdict: confounded

component: systemprompt.md
candidates: agg1
change: Merged the two: dom1's rules compressed into one "Rules:" step, inv1's "read in full / re-read a cut-off view with cat" step, "run calc_sla.py as a cross-check… fix once at most", and "re-open audit_result.json: exact schema…".
observed: agg1.md made one `cat` whose recorded contracts.md view cuts off at "60 " (the same cut that base1 shows after the GLOBEX header). It did not re-read, never ran calc_sla.py, and never re-opened the JSON. It said it "did not open or run" the other workspace files, so the cross-check step was skipped outright. No net-invoice hedge, the same as dom1, whose prompt also has the explicit net rule. It was the fastest run (14.3s). Deliverable identical to base1. None of the procedural steps added in this candidate shows up in its trajectory.
verdict: no observed effect

component: scripts/calc_sla.py
candidates: inv1, agg1 (same file); dom1 (different form)
change: Both forms replace the naive base script (UTC prefix "2026-07", no dedup, hard-coded tiers chosen by fee size, remaining = total). inv1/agg1 form: parses fee, timezone and tiers from contracts.md; uses zoneinfo with a fixed-offset fallback; dedupes keeping RESOLVED and not SUPERSEDED; prints a per-incident trace to stderr; exits non-zero if no tiers parse; takes the directory as an argument. dom1 form: same logic, but cwd-only, no zoneinfo fallback, credit computed from the INVOICE sum instead of the contract fee, trace on stdout.
observed: In none of the four trajectories (base1, inv1, dom1, agg1) did the solver run any version of the script. That includes base1, whose prompt said only "run the script and finish" and whose script would have given wrong minutes. The candidate rollouts are no exception: their prompts cast the script as the main path (inv1) or as a cross-check (dom1, agg1). Neither the naive base script nor either rewrite ever affected a deliverable. The claim in decisions/inv1.md that the script "reproduces base1's values" came from the proposer, not from any solver run.
verdict: no observed effect

component: plugin/README.md, skills/README.md, sub_agents/README.md, scripts/README.md
candidates: inv1, dom1, agg1
change: Added scaffold placeholder comments that describe how to add a plugin, skill, subagent or script. No functional content.
observed: The new directories show up in the `ls -la` output of inv1, dom1 and agg1. No solver opened them (agg1 says outright that it did not). No behavior difference.
verdict: no observed effect
