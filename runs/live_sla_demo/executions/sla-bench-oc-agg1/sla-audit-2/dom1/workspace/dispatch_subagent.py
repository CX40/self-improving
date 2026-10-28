"""Built-in runtime dispatcher for sub_agents/<name>/AGENT.md across model tiers (haiku/sonnet/opus)."""
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
    m_mod = re.search(r"^model:\s*(haiku|sonnet|opus)", raw[:600], re.M | re.I)
    if m_mod:
        model = m_mod.group(1).lower()
    m_eff = re.search(r"^effort:\s*(low|medium|high)", raw[:600], re.M | re.I)
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
