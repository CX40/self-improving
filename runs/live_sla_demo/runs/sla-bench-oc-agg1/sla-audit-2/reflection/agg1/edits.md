component: systemprompt.md
candidates: dom1, agg1 (same text); inv1 (different text)
change: Two forms were tried. dom1/agg1 dropped the base line "fast billing assistant, run `python scripts/calc_sla.py` … and finish". In its place they put an auditor framing ("contracts, log and ledger are the controlling sources; never rely on a canned calculation") plus a line telling the solver to load the `sla-reconcile` skill before computing. inv1 wrote a 3-step procedure instead: read all three files, run the rewritten `scripts/calc_sla.py .` and check its stderr, then reopen and check `audit_result.json`. It also added "Workspace facts" giving the Berlin and New York July windows in UTC and the expected numbers for both customers.
observed: No solver followed either form. dom1 and agg1 never loaded a skill; agg1 ends by saying it "did not open or run" `systemprompt.md`, `dispatch_subagent.py` or the directories. inv1 skipped step 2 ("The inputs are small, so I'll work through them by hand") and step 3 (it wrote the file and never read it back). base1 behaved the same way under the base prompt: it ignored "run calc_sla.py" and computed by hand. All four JSON files are identical (125/4000/3700/4000 and 75/600/500/5400). The replies differ a little. base1 and inv1 added a note that net invoice does not subtract PRE_CREDIT, and inv1's version gets it wrong ("5,000 for UMBRELLA_US"; the correct figure is 5,300). dom1 and agg1 left the note out. base1 added the note with no prompt asking for it, so this difference can't be pinned on the edit. inv1 put the expected answers in the prompt, so its run can't show it worked them out on its own.
verdict: no observed effect

component: scripts/calc_sla.py
candidates: dom1, agg1 (deleted); inv1 (rewritten)
change: Base had a naive script: it matched months by UTC prefix, did no dedup, guessed tiers from the fee amount, and ignored PRE_CREDIT. dom1/agg1 deleted it. inv1 rewrote it to parse fee, timezone and tiers from `contracts.md`, convert starts to local time, dedup keeping the RESOLVED record, subtract PRE_CREDIT, log decisions to stderr and exit non-zero if a contract won't parse.
observed: No run executed any script. base1 never ran the naive one even though its prompt said to, so the bug the edits fix never showed up in a run. It is visible only by reading the file, which is how the agg1 decision justifies the deletion. inv1's solver did not run the rewritten version.
verdict: no observed effect

component: skills/sla-reconcile/SKILL.md
candidates: dom1, agg1
change: New on-demand skill with 7 rules: contract-timezone month window by local start time, OUTAGE only, dedup by incident_id keeping RESOLVED, per-contract tiers, remaining = credit − |PRE_CREDIT|, net = base − credit with the PRE_CREDIT note in the reply, exact schema. It also points to the checker script.
observed: No run loaded it. The trajectories show no skill call; dom1 and agg1 read the inputs and wrote JSON directly. Rule 6 says to put the PRE_CREDIT note in the reply, yet neither dom1 nor agg1 did, which fits the skill never having been read.
verdict: no observed effect

component: skills/sla-reconcile/scripts/sla_check.py
candidates: dom1, agg1
change: New checker script: parses contracts and tiers, falls back to the contract's fixed UTC offset if tzdata is missing, dedups, prints a per-incident COUNT/skip table and writes `audit_result.json`. The year and month are hard-coded as 2026-07.
observed: Never run in any rollout. Only dom1's own design-time check against `context/source` exercised it.
verdict: no observed effect

component: plugin/README.md, scripts/README.md, skills/README.md, sub_agents/README.md
candidates: dom1, agg1, inv1
change: Added one-line HTML-comment placeholders describing each directory. `sub_agents/README.md` asks for `mode: subagent` frontmatter, which doesn't match the task note's `model:`/`effort:` frontmatter for `dispatch_subagent.py`.
observed: Never opened. The solvers only listed the directories. No run delegated to a subagent.
verdict: no observed effect
