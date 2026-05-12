#!/usr/bin/env python3
"""
Efficiency Advisor Loop — Scan Engine
Scans all active projects for efficiency improvement signals.
Reads from ~/.claude/memory/medium-term.md, checks each project,
outputs structured findings for the agent to act on.
"""

import json
import os
import subprocess
import datetime
import uuid
from pathlib import Path

AGENT_DIR = Path.home() / ".claude" / "agents" / "specialized" / "efficiency-advisor-loop"
STATE_FILE = AGENT_DIR / "state.json"

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
    "*/.turbo/*",
    "*/cache/*",
]

SEVERITY_THRESHOLDS = {
    "missing_tests": "medium",
    "missing_cicd": "medium",
    "missing_type_checking": "medium",
    "missing_project_md": "medium",
    "missing_gitignore": "medium",
    "missing_security_headers": "medium",
    "outdated_deps": "medium",
    "git_conflicts": "high",
    "large_untracked": "high",
    "large_node_modules": "low",
    "build_bloat": "low",
    "large_cache_dirs": "low",
    "dependency_sprawl": "low",
    "slow_builds": "low",
    "missing_error_tracking": "medium",
    "memory_drift": "low",
}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "intervalDays": 7,
        "lastRun": None,
        "nextRun": None,
        "scanHistory": [],
        "findings": {},
        "suppressed": [],
    }


def save_state(state: dict) -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    state["lastRun"] = now.isoformat().replace("+00:00", "Z")
    next_run = now + datetime.timedelta(days=state.get("intervalDays", 7))
    state["nextRun"] = next_run.isoformat() + "Z"
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_projects() -> list[dict]:
    """Parse medium-term.md for active project list."""
    mm_path = Path.home() / ".claude" / "memory" / "medium-term.md"
    if not mm_path.exists():
        return []

    content = mm_path.read_text()

    # Find the Active Projects table
    in_table = False
    projects = []
    for line in content.split("\n"):
        if "Active Projects" in line:
            in_table = True
            continue
        if in_table and line.startswith("|------"):
            continue
        if in_table and line.startswith("###"):
            break
        if in_table and line.strip().startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            # parts[0] is empty (leading |), parts[1]=Project, parts[2]=Location, etc.
            if len(parts) >= 4:
                name = parts[1]
                location = parts[2]
                # Skip header row or separator
                if name in ("Project", "") or location in ("Location", ""):
                    continue
                location = location.replace("~", str(Path.home()))
                projects.append({"name": name, "location": location})

    return projects


def check_file_exists(directory: str, patterns: list[str]) -> bool:
    """Check if any of the patterns match a file in the directory."""
    for pattern in patterns:
        matches = list(Path(directory).glob(pattern))
        if matches:
            return True
    return False


def get_dir_size_mb(path: str) -> float:
    """Get total size of directory in MB."""
    if not os.path.isdir(path):
        return 0.0
    try:
        result = subprocess.run(
            ["du", "-sm", path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return float(result.stdout.split()[0])
    except Exception:
        pass
    return 0.0


def check_untracked_large_files(directory: str, threshold_mb: int = 10) -> list[str]:
    """Check for large untracked files in git."""
    git_dir = os.path.join(directory, ".git")
    if not os.path.isdir(git_dir):
        return []

    large_files = []
    try:
        result = subprocess.run(
            ["git", "-C", directory, "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=30,
        )
        for f in result.stdout.strip().split("\n"):
            if not f:
                continue
            fpath = os.path.join(directory, f)
            try:
                size = os.path.getsize(fpath)
                if size > threshold_mb * 1024 * 1024:
                    large_files.append(f"{f} ({size // (1024*1024)}MB)")
            except OSError:
                pass
    except Exception:
        pass
    return large_files


def check_git_conflicts(directory: str) -> bool:
    """Check for unresolved git conflicts."""
    git_dir = os.path.join(directory, ".git")
    if not os.path.isdir(git_dir):
        return False
    merge_head = os.path.join(git_dir, "MERGE_HEAD")
    return os.path.exists(merge_head)


def check_memory_drift(directory: str, threshold_days: int = 14) -> bool:
    """Check if project's memory/ directory hasn't been updated recently."""
    memory_dir = Path(directory) / "memory"
    if not memory_dir.is_dir():
        return True  # No memory dir at all — drift

    cutoff = datetime.datetime.now() - datetime.timedelta(days=threshold_days)
    has_recent = False
    for f in memory_dir.rglob("*"):
        if f.is_file():
            try:
                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > cutoff:
                    has_recent = True
                    break
            except OSError:
                pass
    return not has_recent


def count_deps(package_json_path: str) -> int:
    """Count direct dependencies in package.json."""
    try:
        with open(package_json_path) as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        return len(deps) + len(dev_deps)
    except Exception:
        return 0


def detect_stacks(directory: str) -> list[str]:
    """Detect tech stacks from project files."""
    stacks = []
    root = Path(directory)

    if (root / "package.json").exists():
        stacks.append("node")
        try:
            with open(root / "package.json") as f:
                data = json.load(f)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                stacks.append("nextjs")
            if "react" in deps:
                stacks.append("react")
            if "vue" in deps:
                stacks.append("vue")
            if "@sveltejs/kit" in deps or "svelte" in deps:
                stacks.append("svelte")
        except Exception:
            pass

    if (root / "Cargo.toml").exists():
        stacks.append("rust")
        if any((root / p).exists() for p in ["src-tauri", "tauri.conf.json"]):
            stacks.append("tauri")

    if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
        stacks.append("python")
        if (root / "app").exists() or (root / "main.py").exists():
            try:
                for f in (root / "app").rglob("*.py"):
                    content = f.read_text()
                    if "fastapi" in content or "FastAPI" in content:
                        stacks.append("fastapi")
                        break
            except Exception:
                pass

    if (root / "next.config.js").exists() or (root / "next.config.mjs").exists():
        if "nextjs" not in stacks:
            stacks.append("nextjs")

    # Vercel detection
    if (root / ".vercel").exists() or (root / "vercel.json").exists():
        stacks.append("vercel")

    # PostgreSQL
    for f in root.rglob("*.sql"):
        try:
            if "CREATE TABLE" in f.read_text():
                stacks.append("postgresql")
                break
        except Exception:
            pass

    return stacks


def scan_project(project: dict) -> dict:
    """Scan a single project and return findings."""
    name = project["name"]
    location = project["location"]

    findings = []
    stacks = []

    if not os.path.isdir(location):
        return {
            "name": name,
            "location": location,
            "status": "not_found",
            "signals": [],
            "stacks": [],
            "signalCount": 0,
            "mediumOrHigher": 0,
            "highSeverity": 0,
        }

    stacks = detect_stacks(location)
    root = Path(location)

    # Check .gitignore
    if not (root / ".gitignore").exists():
        findings.append({"type": "missing_gitignore", "severity": "medium", "detail": "No .gitignore in project root"})

    # Check PROJECT.md
    if not (root / "PROJECT.md").exists():
        findings.append({"type": "missing_project_md", "severity": "medium", "detail": "No PROJECT.md in project root"})

    # Check test coverage
    test_dirs = list(root.glob("test")) + list(root.glob("tests")) + list(root.glob("__tests__"))
    test_files = list(root.rglob("*_test.py")) + list(root.rglob("*.test.ts")) + list(root.rglob("*.spec.ts")) + list(root.rglob("*.test.tsx"))
    if not test_dirs and not test_files:
        findings.append({"type": "missing_tests", "severity": "medium", "detail": "No test directory or test files found"})

    # Check CI/CD
    cicd_dirs = list(root.glob(".github/workflows")) + list(root.glob(".github/actions"))
    cicd_files = list(root.glob("vercel.json")) + list(root.glob("netlify.toml")) + list(root.glob(".vercel"))
    if not cicd_dirs and not cicd_files:
        findings.append({"type": "missing_cicd", "severity": "medium", "detail": "No CI/CD configuration found"})

    # Check type checking
    has_tsconfig = (root / "tsconfig.json").exists()
    has_mypy = (root / "mypy.ini").exists() or (root / ".mypy.ini").exists()
    has_pyright = (root / "pyrightconfig.json").exists()
    if not has_tsconfig and not has_mypy and not has_pyright:
        if "node" in stacks or "rust" in stacks:
            findings.append({"type": "missing_type_checking", "severity": "medium", "detail": "No TypeScript config (tsconfig.json) found"})
        elif "python" in stacks:
            findings.append({"type": "missing_type_checking", "severity": "medium", "detail": "No type checking config (mypy/pyright) found"})

    # Check error tracking
    error_files = list(root.glob("sentry.*")) + list(root.glob("*error*monitoring*"))
    if not error_files:
        findings.append({"type": "missing_error_tracking", "severity": "medium", "detail": "No error tracking / Sentry configuration found"})

    # Check security headers (Next.js specific)
    if "nextjs" in stacks:
        next_config = root / "next.config.js"
        if next_config.exists():
            content = next_config.read_text()
            if "headers" not in content and "securityHeaders" not in content:
                findings.append({"type": "missing_security_headers", "severity": "medium", "detail": "No security headers configured in next.config.js"})
        else:
            findings.append({"type": "missing_security_headers", "severity": "low", "detail": "No next.config.js found"})

    # Size checks
    nm_size = get_dir_size_mb(os.path.join(location, "node_modules"))
    if nm_size > 500:
        findings.append({"type": "large_node_modules", "severity": "low", "detail": f"node_modules is {nm_size:.0f}MB (threshold: 500MB)"})

    for build_dir in ["dist", "build", ".next", "target"]:
        bd_size = get_dir_size_mb(os.path.join(location, build_dir))
        if bd_size > 200:
            findings.append({"type": "build_bloat", "severity": "low", "detail": f"{build_dir} is {bd_size:.0f}MB — may indicate unchecked builds"})

    # Cache dirs
    for cache_dir in [".turbo", "cache"]:
        cd_size = get_dir_size_mb(os.path.join(location, cache_dir))
        if cd_size > 200:
            findings.append({"type": "large_cache_dirs", "severity": "low", "detail": f"{cache_dir} is {cd_size:.0f}MB"})

    # Dependency count
    pkg_json = root / "package.json"
    if pkg_json.exists():
        dep_count = count_deps(str(pkg_json))
        if dep_count > 200:
            findings.append({"type": "dependency_sprawl", "severity": "low", "detail": f"{dep_count} direct dependencies — potential dependency sprawl"})

    # Git conflicts
    if check_git_conflicts(location):
        findings.append({"type": "git_conflicts", "severity": "high", "detail": "Unresolved git merge conflict detected"})

    # Large untracked files
    large_untracked = check_untracked_large_files(location)
    if large_untracked:
        findings.append({"type": "large_untracked", "severity": "high", "detail": f"Large untracked files: {', '.join(large_untracked[:3])}"})

    # Memory drift
    if check_memory_drift(location):
        findings.append({"type": "memory_drift", "severity": "low", "detail": "memory/ directory not updated in 14+ days"})

    # Stack-specific: Rust Cargo.lock
    if "rust" in stacks:
        if not (root / "Cargo.lock").exists():
            findings.append({"type": "missing_cargo_lock", "severity": "medium", "detail": "Cargo.lock not committed — builds may be non-deterministic"})

    # Stack-specific: Python hash pinning
    if "python" in stacks:
        req_txt = root / "requirements.txt"
        if req_txt.exists():
            content = req_txt.read_text()
            if not any(line.startswith("#") and "hash" in content for line in content.split("\n")):
                findings.append({"type": "outdated_deps", "severity": "low", "detail": "requirements.txt without hash pinning — consider pip-compile or poetry.lock"})

    return {
        "name": name,
        "location": location,
        "status": "scanned",
        "stacks": stacks,
        "signals": findings,
        "signalCount": len(findings),
        "mediumOrHigher": sum(1 for f in findings if f["severity"] in ("high", "medium")),
        "highSeverity": sum(1 for f in findings if f["severity"] == "high"),
    }


def run_scan() -> dict:
    """Run full efficiency scan across all projects."""
    state = load_state()
    projects = get_projects()

    scan_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    all_findings = {}
    total_signals = 0
    projects_with_issues = 0
    high_issues = 0

    for project in projects:
        result = scan_project(project)
        all_findings[project["name"]] = result
        total_signals += result["signalCount"]
        if result["mediumOrHigher"] > 0:
            projects_with_issues += 1
        high_issues += result.get("highSeverity", 0)

    # Build suppressed lookup
    now = datetime.datetime.utcnow()
    suppressed_lookup = {}
    for item in state.get("suppressed", []):
        until = datetime.datetime.fromisoformat(item["until"].replace("Z", "+00:00").replace("+00:00", ""))
        if datetime.datetime.now() < until:
            key = (item["project"], item["signal"])
            suppressed_lookup[key] = item["until"]

    # Apply suppressions
    for proj_name, proj_data in all_findings.items():
        filtered_signals = []
        for sig in proj_data.get("signals", []):
            key = (proj_name, sig["type"])
            if key in suppressed_lookup:
                continue
            filtered_signals.append(sig)
        proj_data["signals"] = filtered_signals
        proj_data["signalCount"] = len(filtered_signals)
        proj_data["mediumOrHigher"] = sum(1 for f in filtered_signals if f["severity"] in ("high", "medium"))

    # Update state
    scan_record = {
        "scanId": scan_id,
        "timestamp": timestamp,
        "projectsScanned": [p["name"] for p in projects],
        "totalSignals": total_signals,
        "highIssues": high_issues,
        "projectsWithIssues": projects_with_issues,
    }
    state["scanHistory"].append(scan_record)
    state["findings"] = all_findings
    save_state(state)

    output = {
        "scanId": scan_id,
        "timestamp": timestamp,
        "projectsScanned": [p["name"] for p in projects],
        "projectsSkipped": [],
        "totalSignals": total_signals,
        "highIssues": high_issues,
        "projectsWithIssues": projects_with_issues,
        "requiresBODConsultation": high_issues > 0 or projects_with_issues > 0,
        "findings": all_findings,
    }

    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    run_scan()
