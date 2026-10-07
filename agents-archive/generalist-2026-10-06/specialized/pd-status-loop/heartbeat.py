#!/usr/bin/env python3
"""
PD Status Loop — Heartbeat Engine
Runs on a cron schedule (every 60 min). Determines who to ping vs skip,
updates state, and outputs structured results for the cron trigger to act on.
"""

import json
import os
import re
import subprocess
import glob
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path.home() / ".claude" / "agents" / "specialized" / "pd-status-loop"
STATE_FILE = AGENT_DIR / "state.json"

INTERVAL_NORMAL = 120   # minutes
INTERVAL_CATCHUP = 60   # minutes
ACTIVITY_THRESHOLD = 90  # minutes — skip if files changed in last 90 min
MAX_PDS = 5

EXCLUDE_PATTERNS = [
    "*/node_modules/*",
    "*/.git/*",
    "*/target/*",
    "*/.next/*",
    "*/dist/*",
    "*/build/*",
    "*/.venv/*",
    "*/__pycache__/*",
    "*/vendor/*",
    "*/coverage/*",
    "*/tmp/*",
]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "lastRun": None,
        "currentCycleMinutes": INTERVAL_NORMAL,
        "pdState": {},
    }


def save_state(state: dict) -> None:
    state["lastRun"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    STATE_FILE.write_text(json.dumps(state, indent=2))


def discover_pds() -> list[dict]:
    """Discover all PDs from team config files. Returns sorted list of dicts."""
    pds = []
    teams_base = str(Path.home() / ".claude" / "teams")
    for cfg_path in glob.glob(f"{teams_base}/*/config.json"):
        try:
            cfg = json.loads(Path(cfg_path).read_text())
        except Exception:
            continue
        for m in cfg.get("members", []):
            name = m.get("name", "")
            if not name.endswith("-pd"):
                continue
            prompt = m.get("prompt", "")
            m_dir = re.search(r"Location:\s*([^\s\n]+)", prompt)
            project = re.search(r"\*\*The Project — ([^*:]+)", prompt)
            pd_dir = m_dir.group(1).replace("~", str(Path.home())) if m_dir else ""
            pds.append({
                "name": name,
                "project": project.group(1).strip() if project else name.replace("-pd", ""),
                "projectDir": pd_dir,
            })
    pds.sort(key=lambda x: x["name"])
    return pds[:MAX_PDS]


def is_project_active(project_dir: str) -> tuple[bool, str]:
    """Returns (is_active, last_activity_str)."""
    if not project_dir or not os.path.isdir(project_dir):
        return False, "project dir not found"

    exclude_args = []
    for pat in EXCLUDE_PATTERNS:
        exclude_args += ["-not", "-path", pat]

    try:
        result = subprocess.run(
            ["find", project_dir, "-type", "f", *exclude_args, "-mmin", f"-{ACTIVITY_THRESHOLD}"],
            capture_output=True, text=True, timeout=30,
        )
        files = [f for f in result.stdout.strip().split("\n") if f]
        if files:
            latest = subprocess.run(
                ["find", project_dir, "-type", "f", *exclude_args, "-mmin", f"-{ACTIVITY_THRESHOLD}", "-printf", "%T@\n"],
                capture_output=True, text=True, timeout=30,
            )
            timestamps = [float(t) for t in latest.stdout.strip().split("\n") if t.strip()]
            if timestamps:
                last_change = datetime.fromtimestamp(max(timestamps), tz=timezone.utc)
                return True, last_change.strftime("%Y-%m-%d %H:%M")
            return True, "recent activity"
        return False, "no recent file changes"
    except Exception as e:
        return False, f"error: {e}"


def run_heartbeat():
    state = load_state()

    # Sync PDs from team configs into state
    pds = discover_pds()
    known_names = set(state["pdState"].keys())

    for pd in pds:
        if pd["name"] not in state["pdState"]:
            state["pdState"][pd["name"]] = {
                "project": pd["project"],
                "projectDir": pd["projectDir"],
                "lastPinged": None,
                "lastSkipped": False,
                "skippedCount": 0,
            }

    for name in known_names - {pd["name"] for pd in pds}:
        del state["pdState"][name]

    # Determine cycle: if any PD was skipped last run, use catchup interval
    any_skipped = any(pd.get("lastSkipped", False) for pd in state["pdState"].values())
    cycle_minutes = INTERVAL_CATCHUP if any_skipped else INTERVAL_NORMAL

    # Check activity for each PD
    to_ping = []
    to_skip = []
    all_reports = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for pd in pds:
        active, last_activity = is_project_active(pd["projectDir"])
        info = {
            "name": pd["name"],
            "project": pd["project"],
            "projectDir": pd["projectDir"],
            "active": active,
            "lastActivity": last_activity,
        }
        all_reports.append(info)
        if active:
            to_skip.append(pd)
        else:
            to_ping.append(pd)

    # Update state
    pinged_names = []
    skipped_names = []
    state["currentCycleMinutes"] = cycle_minutes

    for pd in pds:
        pd_state = state["pdState"][pd["name"]]
        if pd in to_ping:
            pd_state["lastPinged"] = now
            pd_state["lastSkipped"] = False
            pd_state["skippedCount"] = 0
            pinged_names.append(pd["name"])
        else:
            pd_state["lastSkipped"] = True
            pd_state["skippedCount"] = pd_state.get("skippedCount", 0) + 1
            skipped_names.append(pd["name"])

    save_state(state)

    output = {
        "timestamp": now,
        "cycleMinutes": cycle_minutes,
        "pdsDiscovered": len(pds),
        "pinged": pinged_names,
        "skipped": skipped_names,
        "reports": all_reports,
        "nextCycleMinutes": INTERVAL_NORMAL if not to_skip else INTERVAL_CATCHUP,
    }

    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    run_heartbeat()
