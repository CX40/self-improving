"""Live Multi-Tier Harness² Demo using local Claude subscription (Haiku / Sonnet / Opus).

Demonstrates:
1. Task-level recursion (Propose -> Probe -> Compose) over the 8-component OpenCode harness
   (systemprompt.md, guardrails.md, LongTermMEMORY.md, tool_guidance.md, skills/, sub_agents/, scripts/, plugin/).
2. Multi-tier model dispatching: The executor supports spawning subagents defined in `sub_agents/<name>/AGENT.md`
   on specific model tiers (`model: haiku | sonnet | opus` and `effort: low | medium | high`) via `scripts/dispatch_subagent.py`
   or running deterministic helper scripts in `scripts/`.
3. Harnessing-level recursion: Learning from Task 1 into `library/.../EXPERIENCE.md` and reusing that library on Task 2.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Force all temporary files onto D:
TMP_ROOT = Path("D:/DEV/AI/self-improving/tmp")
TMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TMP_ROOT)
os.environ["TMP"] = str(TMP_ROOT)
os.environ["TMPDIR"] = str(TMP_ROOT)

from harness2.core import tree
from harness2.core.proposer import Proposer
from harness2.core.schedule import run_domain
from harness2.core.spec import BenchPrompts, BenchSpec, ChannelSpec
from harness2.substrate.opencode import OpencodeSubstrate


DISPATCH_HELPER = '''"""Built-in runtime dispatcher for sub_agents/<name>/AGENT.md across model tiers (haiku/sonnet/opus)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage: python dispatch_subagent.py <subagent_name> <prompt_or_file>")
        sys.exit(1)
    name = sys.argv[1]
    prompt_arg = sys.argv[2]
    agent_file = Path("sub_agents") / name / "AGENT.md"
    if not agent_file.is_file():
        print(f"Error: {agent_file} not found", file=sys.stderr)
        sys.exit(1)
    raw = agent_file.read_text(encoding="utf-8")
    model = "haiku"
    effort = "low"
    m_mod = re.search(r"^model:\\s*(haiku|sonnet|opus)", raw[:600], re.M | re.I)
    if m_mod:
        model = m_mod.group(1).lower()
    m_eff = re.search(r"^effort:\\s*(low|medium|high)", raw[:600], re.M | re.I)
    if m_eff:
        effort = m_eff.group(1).lower()

    if Path(prompt_arg).is_file():
        task_input = Path(prompt_arg).read_text(encoding="utf-8")
    else:
        task_input = prompt_arg

    cli = shutil.which("claude") or "claude"
    cmd = [
        cli, "--dangerously-skip-permissions", "-p",
        "--output-format", "json",
        "--model", model,
        "--effort", effort,
        "--append-system-prompt", raw,
    ]
    p = subprocess.run(
        cmd, input=task_input, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180
    )
    try:
        payload = json.loads(p.stdout.strip().splitlines()[-1])
        out = payload.get("result") or payload.get("text") or p.stdout
    except Exception:
        out = p.stdout
    print(f"[SUBAGENT {name} | model={model} effort={effort}]")
    print(out)

if __name__ == "__main__":
    main()
'''


TASK_1_FILES = {
    "contracts.md": """# SLA & Billing Contracts (Q3-2026)

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
""",
    "incidents.log": """incident_id,customer,start_utc,duration_min,status,notes
INC-101,ACME_CORP,2026-06-30T22:30:00Z,40,OUTAGE,Database failover (Note: 2026-07-01 00:30 CEST in Berlin!)
INC-102,ACME_CORP,2026-07-12T10:00:00Z,65,MAINTENANCE,Scheduled kernel patching window
INC-103,ACME_CORP,2026-07-19T14:15:00Z,35,OUTAGE,Primary router packet drop
INC-104,ACME_CORP,2026-07-31T22:15:00Z,50,OUTAGE,Storage cluster stall (Note: 2026-08-01 00:15 CEST in Berlin - August!)
INC-201,GLOBEX_INC,2026-07-01T02:00:00Z,55,OUTAGE,Edge proxy crash (Note: 2026-06-30 22:00 EDT in New York - June!)
INC-202,GLOBEX_INC,2026-07-15T16:00:00Z,50,OUTAGE,Initial telemetry estimate (SUPERSEDED)
INC-202,GLOBEX_INC,2026-07-15T16:00:00Z,50,OUTAGE,RESOLVED final record after deduplication
INC-203,GLOBEX_INC,2026-07-22T09:00:00Z,30,DEGRADED,Elevated latency only
INC-204,GLOBEX_INC,2026-08-01T01:30:00Z,45,OUTAGE,Auth node timeout (Note: 2026-07-31 21:30 EDT in New York - still July!)
""",
    "ledger_adjustments.csv": """entry_id,customer,type,amount_usd,memo
ADJ-01,ACME_CORP,INVOICE,12000.00,July 2026 Base Fee
ADJ-02,ACME_CORP,PRE_CREDIT,-500.00,Goodwill credit already applied to July invoice for SLA
ADJ-03,GLOBEX_INC,INVOICE,4500.00,July 2026 Base Fee
ADJ-04,GLOBEX_INC,PRE_CREDIT,0.00,No prior credit applied
""",
}

# Ground truth for Task 1 (never shown to solver or improver!):
# ACME_CORP (Europe/Berlin = UTC+2):
#   - INC-101: 2026-06-30 22:30 UTC = 2026-07-01 00:30 CEST -> IN JULY! (40 min, OUTAGE)
#   - INC-102: MAINTENANCE -> ignored (0 min)
#   - INC-103: 2026-07-19 14:15 UTC -> IN JULY! (35 min, OUTAGE)
#   - INC-104: 2026-07-31 22:15 UTC = 2026-08-01 00:15 CEST -> AUGUST! Ignored!
#   Total July Outage = 40 + 35 = 75 min -> 60..119 min tier = 25% of $12,000 = $3,000.00 SLA credit.
#   Already applied pre-credit: $500.00 -> Remaining Credit Due = $2,500.00. Net Final Invoice = $12,000 - $3,000 = $9,000.00.
# GLOBEX_INC (America/New_York = UTC-4):
#   - INC-201: 2026-07-01 02:00 UTC = 2026-06-30 22:00 EDT -> JUNE! Ignored!
#   - INC-202: listed twice (50 min), deduplicated -> 50 min OUTAGE in July.
#   - INC-203: DEGRADED -> ignored (0 min)
#   - INC-204: 2026-08-01 01:30 UTC = 2026-07-31 21:30 EDT -> IN JULY! (45 min, OUTAGE)
#   Total July Outage = 50 + 45 = 95 min -> >=90 min tier = 20% of $4,500 = $900.00 SLA credit.
#   Already applied pre-credit: $0.00 -> Remaining Credit Due = $900.00. Net Final Invoice = $4,500 - $900 = $3,600.00.


TASK_2_FILES = {
    "contracts.md": """# SLA & Billing Contracts (Q3-2026 — Batch B)

## Customer: INITECH_DE (Plan: Enterprise-SLA)
- Monthly Base Fee: $8,000.00
- Billing Timezone: **Europe/Berlin (UTC+2 in Summer / CEST)** — All contract month boundaries are evaluated in Customer Local Time!
- SLA Downtime Credit Rule:
  - Only **UNPLANNED** outages (`status=OUTAGE`) in the target billing month (July 2026 in Customer Local Time) count toward SLA downtime.
  - Duplicate incident IDs in logs must be deduplicated (keep the final `RESOLVED` record for that `incident_id`).
  - If total valid unplanned downtime in July 2026 is:
    - < 30 minutes: 0% credit
    - 30 to 59 minutes: 10% of Monthly Base Fee ($800.00)
    - 60 to 119 minutes: 25% of Monthly Base Fee ($2,000.00)
    - >= 120 minutes: 50% of Monthly Base Fee ($4,000.00)

## Customer: UMBRELLA_US (Plan: Growth-SLA)
- Monthly Base Fee: $6,000.00
- Billing Timezone: **America/New_York (UTC-4 in Summer / EDT)** — All contract month boundaries are evaluated in Customer Local Time!
- SLA Downtime Credit Rule:
  - Only **UNPLANNED** outages (`status=OUTAGE`) in the target billing month (July 2026 in Customer Local Time) count toward SLA downtime.
  - Scheduled maintenance (`status=MAINTENANCE`) or degraded performance (`status=DEGRADED`) do NOT count.
  - If total valid unplanned downtime in July 2026 is:
    - < 45 minutes: 0% credit
    - 45 to 89 minutes: 10% of Monthly Base Fee ($600.00)
    - >= 90 minutes: 20% of Monthly Base Fee ($1,200.00)
""",
    "incidents.log": """incident_id,customer,start_utc,duration_min,status,notes
INC-301,INITECH_DE,2026-06-30T23:00:00Z,45,OUTAGE,API gateway restart (2026-07-01 01:00 CEST in Berlin -> July!)
INC-302,INITECH_DE,2026-07-10T12:00:00Z,80,OUTAGE,Preliminary noisy alert (SUPERSEDED)
INC-302,INITECH_DE,2026-07-10T12:00:00Z,80,OUTAGE,RESOLVED confirmed 80 min outage
INC-303,INITECH_DE,2026-07-31T22:30:00Z,30,OUTAGE,Cache flush (2026-08-01 00:30 CEST in Berlin -> August!)
INC-401,UMBRELLA_US,2026-07-01T01:00:00Z,60,OUTAGE,DNS glitch (2026-06-30 21:00 EDT in New York -> June!)
INC-402,UMBRELLA_US,2026-07-18T15:00:00Z,50,OUTAGE,Storage node drop
INC-403,UMBRELLA_US,2026-07-25T18:00:00Z,45,MAINTENANCE,Planned upgrade
INC-404,UMBRELLA_US,2026-08-01T02:00:00Z,25,OUTAGE,Queue stall (2026-07-31 22:00 EDT in New York -> July!)
""",
    "ledger_adjustments.csv": """entry_id,customer,type,amount_usd,memo
ADJ-11,INITECH_DE,INVOICE,8000.00,July 2026 Base Fee
ADJ-12,INITECH_DE,PRE_CREDIT,-300.00,Goodwill credit already applied to July invoice
ADJ-13,UMBRELLA_US,INVOICE,6000.00,July 2026 Base Fee
ADJ-14,UMBRELLA_US,PRE_CREDIT,-100.00,Goodwill credit already applied to July invoice
""",
}

# Ground truth for Task 2:
# INITECH_DE (UTC+2):
#   - INC-301: 45 min (July)
#   - INC-302: 80 min (deduplicated, July)
#   - INC-303: August -> ignored
#   Total = 125 min (>=120 min -> 50% of $8,000 = $4,000.00). Pre-credit = $300 -> Remaining Credit Due = $3,700.00. Net Final Invoice = $4,000.00.
# UMBRELLA_US (UTC-4):
#   - INC-401: June -> ignored
#   - INC-402: 50 min (July)
#   - INC-403: MAINTENANCE -> ignored
#   - INC-404: 25 min (July)
#   Total = 75 min (45..89 min -> 10% of $6,000 = $600.00). Pre-credit = $100 -> Remaining Credit Due = $500.00. Net Final Invoice = $5,400.00.


GROUND_TRUTH = {
    "sla-audit-1": {
        "ACME_CORP": {"valid_downtime_min": 75, "total_sla_credit_usd": 3000.00, "remaining_credit_due_usd": 2500.00, "net_final_invoice_usd": 9000.00},
        "GLOBEX_INC": {"valid_downtime_min": 95, "total_sla_credit_usd": 900.00, "remaining_credit_due_usd": 900.00, "net_final_invoice_usd": 3600.00},
    },
    "sla-audit-2": {
        "INITECH_DE": {"valid_downtime_min": 125, "total_sla_credit_usd": 4000.00, "remaining_credit_due_usd": 3700.00, "net_final_invoice_usd": 4000.00},
        "UMBRELLA_US": {"valid_downtime_min": 75, "total_sla_credit_usd": 600.00, "remaining_credit_due_usd": 500.00, "net_final_invoice_usd": 5400.00},
    },
}


# The Base Harness starts with a fast/naive script that has typical real-world bugs:
# 1) It slices start_utc[:7] == "2026-07" in UTC without converting to the customer's billing timezone
# 2) It doesn't deduplicate repeated incident_ids
# 3) It forgets to subtract PRE_CREDIT from remaining_credit_due_usd
NAIVE_BASE_SCRIPT = '''"""Base quick calculator for SLA audit."""
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
'''


class MultiTierClaudeAdapter:
    """Executes tasks using the 8-component OpenCode harness tree and local Claude CLI (Haiku/Sonnet/Opus)."""

    def __init__(self, root: Path, solver_model: str = "haiku", improver_model: str = "sonnet"):
        self.root = root
        self.solver_model = solver_model
        self.improver_model = improver_model
        self.substrate = OpencodeSubstrate()
        self.spec = BenchSpec(
            name="sla-bench",
            runs_root=root / "runs",
            install_mode="workspace_config",
            prompts=BenchPrompts(
                work=(
                    "audit SLA downtime logs, contract timezone rules, and prior ledger credits "
                    "to produce an exact JSON reconciliation deliverable (`audit_result.json`). "
                    "Note: The runtime workspace includes `dispatch_subagent.py` so the solver can "
                    "delegate bounded sub-tasks to `sub_agents/<name>/AGENT.md` with YAML frontmatter "
                    "`model: haiku|sonnet|opus` and `effort: low|medium|high` via "
                    "`python dispatch_subagent.py <name> <prompt>`"
                ),
            ),
            channels={
                "proposer": ChannelSpec("claude_cli", improver_model, effort="medium", timeout=300),
                "selector": ChannelSpec("claude_cli", improver_model, effort="medium", timeout=300),
            },
            leak_globs=("ground_truth.json",),
        )
        self.execution_count = 0

        # Initialize the Base Harness H_0
        base = {name: "" for name in self.substrate.surface().always_on}
        base["systemprompt.md"] = (
            "You are a fast billing assistant. Run `python scripts/calc_sla.py` to generate "
            "`audit_result.json` quickly and finish.\n"
        )
        base["scripts/calc_sla.py"] = NAIVE_BASE_SCRIPT
        tree.write_tree(self.substrate.surface(), base, self.base_harness(), stubs=False)

        for task_id, files in (("sla-audit-1", TASK_1_FILES), ("sla-audit-2", TASK_2_FILES)):
            src = self.task_files(task_id)
            src.mkdir(parents=True, exist_ok=True)
            for fname, content in files.items():
                (src / fname).write_text(content, encoding="utf-8")

    def tasks(self, split: str = "all") -> list[str]:
        return ["sla-audit-1", "sla-audit-2"]

    def domain_of(self, task_id: str) -> str:
        return "sla_reconciliation"

    def task_prompt(self, task_id: str) -> str:
        return (
            "Reconcile the July 2026 SLA downtime credits for all customers in `contracts.md`, "
            "`incidents.log`, and `ledger_adjustments.csv`.\n\n"
            "Write the final result to `audit_result.json` with this exact JSON schema:\n"
            "```json\n"
            "{\n"
            '  "customers": {\n'
            '    "<CUSTOMER_ID>": {\n'
            '      "valid_downtime_min": <int>,\n'
            '      "total_sla_credit_usd": <float>,\n'
            '      "remaining_credit_due_usd": <float>,\n'
            '      "net_final_invoice_usd": <float>\n'
            "    }\n"
            "  }\n"
            "}\n"
            "```\n"
            "Definitions:\n"
            "- `valid_downtime_min`: Sum of valid unplanned outage minutes falling within July 2026 in the customer's contract billing timezone, after deduplicating repeated incident IDs.\n"
            "- `total_sla_credit_usd`: Full SLA credit earned for July 2026 based on the contract tier.\n"
            "- `remaining_credit_due_usd`: Additional credit still owed to the customer after subtracting any `PRE_CREDIT` already applied in `ledger_adjustments.csv`.\n"
            "- `net_final_invoice_usd`: Final invoice amount (`INVOICE` base fee minus `total_sla_credit_usd`).\n"
        )

    def task_files(self, task_id: str) -> Path:
        return self.root / "sources" / task_id

    def base_harness(self) -> Path:
        return self.root / "base"

    def validate_tree(self, harness: tree.Tree) -> None:
        pass

    def _compose_system_prompt(self, harness_dir: Path) -> str:
        parts = []
        for fname in self.substrate.surface().always_on:
            p = harness_dir / fname
            if p.is_file() and p.read_text(encoding="utf-8").strip():
                parts.append(f"## {fname}\n" + p.read_text(encoding="utf-8").strip())
        skills = sorted(harness_dir.glob("skills/*/SKILL.md"))
        if skills:
            s_lines = [f"- `skills/{s.parent.name}/SKILL.md`" for s in skills]
            parts.append("## AVAILABLE SKILLS (read on demand)\n" + "\n".join(s_lines))
        subagents = sorted(harness_dir.glob("sub_agents/*/AGENT.md"))
        if subagents:
            sa_lines = [
                f"- `{sa.parent.name}` (invoke via `python dispatch_subagent.py {sa.parent.name} \"<prompt>\"`)"
                for sa in subagents
            ]
            parts.append("## AVAILABLE SUBAGENTS (multi-model tier dispatch)\n" + "\n".join(sa_lines))
        scripts = sorted(harness_dir.glob("scripts/*.py"))
        if scripts:
            sc_lines = [f"- `scripts/{sc.name}`" for sc in scripts]
            parts.append("## AVAILABLE HELPER SCRIPTS\n" + "\n".join(sc_lines))
        return "\n\n---\n\n".join(parts)

    def execute(
        self, task_id: str, harness_dir: Path | None, run_id: str, *, timeout: int | None = None
    ) -> Path:
        self.execution_count += 1
        h_dir = harness_dir or self.base_harness()
        run_dir = self.root / "executions" / run_id
        shutil.rmtree(run_dir, ignore_errors=True)
        ws = run_dir / "workspace"
        ws.mkdir(parents=True, exist_ok=True)

        # Copy source files, harness files, and the multi-model subagent dispatcher into workspace
        shutil.copytree(self.task_files(task_id), ws, dirs_exist_ok=True)
        shutil.copytree(h_dir, ws, dirs_exist_ok=True)
        (ws / "dispatch_subagent.py").write_text(DISPATCH_HELPER, encoding="utf-8")

        sys_prompt = self._compose_system_prompt(h_dir)
        task_text = self.task_prompt(task_id)

        print(f"    [SOLVER:{self.solver_model}] executing {run_id} ...", flush=True)
        t0 = time.time()
        cli = shutil.which("claude") or "claude"
        cmd = [
            cli,
            "--dangerously-skip-permissions",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.solver_model,
            "--effort",
            "low",
            "--append-system-prompt",
            sys_prompt,
        ]
        p = subprocess.run(
            cmd,
            input=task_text,
            cwd=ws,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout or 240,
        )
        elapsed = round(time.time() - t0, 1)

        # Build human-readable trajectory from stream-json so Harness² improver sees every action & observation
        traj_lines = [f"# Solver Execution ({self.solver_model}, {elapsed}s)\n"]
        final_text = ""
        for raw_line in (p.stdout or "").splitlines():
            raw_line = raw_line.strip()
            if not raw_line.startswith("{"):
                continue
            try:
                evt = json.loads(raw_line)
            except Exception:
                continue
            etype = evt.get("type")
            if etype == "assistant":
                msg = evt.get("message") or {}
                for block in msg.get("content") or []:
                    if block.get("type") == "text":
                        traj_lines.append(f"[ASSISTANT]\n{block.get('text')}\n")
                    elif block.get("type") == "tool_use":
                        traj_lines.append(
                            f"[ACTION] {block.get('name')}({json.dumps(block.get('input', {}))})\n"
                        )
            elif etype == "user":
                msg = evt.get("message") or {}
                for block in msg.get("content") or []:
                    if block.get("type") == "tool_result":
                        content = str(block.get("content") or "")[:1500]
                        traj_lines.append(f"[OBSERVATION]\n{content}\n")
            elif etype == "result":
                final_text = str(evt.get("result") or "")

        (run_dir / "trajectory.md").write_text("\n".join(traj_lines), encoding="utf-8")
        res_file = ws / "audit_result.json"
        if res_file.is_file():
            shutil.copy2(res_file, run_dir / "audit_result.json")
        elif final_text:
            m = re.search(r"\{[\s\S]*\"customers\"[\s\S]*\}", final_text)
            if m:
                (run_dir / "audit_result.json").write_text(m.group(0), encoding="utf-8")
        return run_dir

    def delivered(self, run_dir: Path) -> bool:
        return (run_dir / "audit_result.json").is_file()

    def trajectory(self, run_dir: Path, *, obs_trunc: int = 2000) -> str:
        t = run_dir / "trajectory.md"
        return t.read_text(encoding="utf-8") if t.is_file() else "(no trajectory)"

    def deliverable_text(self, run_dir: Path) -> str:
        f = run_dir / "audit_result.json"
        return f.read_text(encoding="utf-8") if f.is_file() else ""

    def deliverable_files(self, run_dir: Path) -> dict[str, str]:
        if self.delivered(run_dir):
            return {"audit_result.json": self.deliverable_text(run_dir)}
        return {}


def score_deliverable(task_id: str, text: str) -> tuple[float, list[str]]:
    """Independent post-hoc evaluation against GROUND_TRUTH (never seen during Harness² run)."""
    if not text.strip():
        return 0.0, ["Missing audit_result.json"]
    try:
        data = json.loads(text)
    except Exception as e:
        return 0.0, [f"Invalid JSON: {e}"]
    custs = data.get("customers") or {}
    expected = GROUND_TRUTH[task_id]
    total_checks = 0
    passed = 0
    notes = []
    for cid, exp_vals in expected.items():
        got_c = custs.get(cid) or {}
        for field, exp_v in exp_vals.items():
            total_checks += 1
            got_v = got_c.get(field)
            if got_v is not None and abs(float(got_v) - float(exp_v)) < 0.01:
                passed += 1
                notes.append(f"  [OK] {cid}.{field} = {got_v}")
            else:
                notes.append(f"  [MISS] {cid}.{field}: got {got_v!r}, expected {exp_v!r}")
    return round(100.0 * passed / max(1, total_checks), 1), notes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("D:/DEV/AI/self-improving/runs/live_sla_demo"))
    parser.add_argument("--solver", default="haiku", choices=("haiku", "sonnet", "opus"))
    parser.add_argument("--improver", default="sonnet", choices=("haiku", "sonnet", "opus"))
    parser.add_argument("--selector", default="opus", choices=("haiku", "sonnet", "opus"))
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--mode", default="parallel", choices=("parallel", "sequential"))
    args = parser.parse_args()

    root = args.output.resolve()
    adapter = MultiTierClaudeAdapter(root, solver_model=args.solver, improver_model=args.improver)
    # Use asymmetric model routing:
    # - Solver: fast model (haiku)
    # - Improver (Propose / Compose): sonnet
    # - Selector & Experience Reflector: opus (highest reasoning tier)
    adapter.spec.channels["selector"] = ChannelSpec("claude_cli", args.selector, effort="high", timeout=300)

    proposer = Proposer(
        adapter.spec.channels["proposer"],
        audit_dir=root / "audit" / "proposer",
        project="",
    )
    selector = Proposer(
        adapter.spec.channels["selector"],
        audit_dir=root / "audit" / "selector",
        project="",
    )

    mode_tok = "agg" if args.mode == "parallel" else "seq"
    print(
        f"=== Starting Harness² Live Multi-Tier Run ===\n"
        f"  Solver (Base Executor): {args.solver} (can dispatch sub_agents to haiku/sonnet/opus)\n"
        f"  Improver (Propose/Compose): {args.improver}\n"
        f"  Selector & Reflector: {args.selector}\n"
        f"  Mode: {args.mode} (k={args.k})\n"
        f"  Output root: {root}\n",
        flush=True,
    )

    result = run_domain(
        "sla_reconciliation",
        adapter.tasks(),
        args.k,
        adapter=adapter,
        prop=proposer,
        selector_prop=selector,
        runs_root=adapter.spec.runs_root,
        library_root=root / "library" / f"k{args.k}",
        modes=(mode_tok,),
    )

    print("\n=== Post-Hoc Independent Evaluation (Base H_0 vs. Harness² H') ===")
    ns = f"sla-bench-oc-{mode_tok}{args.k}"
    for tid in adapter.tasks():
        base_file = root / "executions" / ns / tid / "base1" / "audit_result.json"
        final_label = "agg1" if mode_tok == "agg" else f"c{args.k}"
        final_file = root / "executions" / ns / tid / final_label / "audit_result.json"

        b_score, b_notes = score_deliverable(tid, base_file.read_text(encoding="utf-8") if base_file.is_file() else "")
        f_score, f_notes = score_deliverable(tid, final_file.read_text(encoding="utf-8") if final_file.is_file() else "")
        print(f"\nTask: {tid}")
        print(f"  Base Harness (H_0) Score:      {b_score:5.1f}%")
        for n in b_notes:
            print("   ", n)
        print(f"  Refined Harness (H') Score:    {f_score:5.1f}%  (Delta: {f_score - b_score:+.1f}%)")
        for n in f_notes:
            print("   ", n)


if __name__ == "__main__":
    main()
