#!/usr/bin/env python3
"""os-cost-report.py: 7-day spawn cost by skill / agent type / project / model, joined to Jev route ids.

Reads EVERY spawns log the ledger can write to (global + each medium-term project + projects/*/memory/spawns.jsonl, via
hooks/lib/spawn_project.py; SPAWN_LOG_FILE + SPAWN_LEDGER_EXTRA_LOGS in tests) and the skill-route decision log
(SKILL_ROUTE_LOG, else {root}/memory/metrics/skill-route.jsonl).
Join: spawn_end -> spawn_start by spawn_id (any log); start.jev_route_id -> route log route_id (EXACT, no fuzzy).
Carries BOTH API-equivalent USD (cost_usd) and raw tokens; no budget enforcement (the budget unit is an open question).
Cost = sum of every spawn_end row in the window (matches a raw ledger sum; continuation rows are included and counted in
`continuation_rows`).
attributed = start row has a jev_route_id that exists in the route log. post_change = start row has the jev_route_id key
(written by ledger.py since B1); older rows are reported separately as pre_change.
With the skill router off (default; AGENCY_SKILL_ROUTER=1 enables it) no spawn carries a Jev route id, so every row lands as
unattributed, while by_skill (from the prompt's Skills: line), by_agent_type, by_project and by_model still work.
Output: {root}/state/os/cost-weekly.json (--out, --route-log, --days, --now to override). Always exits 0."""
import argparse
import collections
import datetime
import json
import os
import re
import sys

HOME = os.path.expanduser("~")


# Python twin of hooks/lib/resolve-root.sh, copied verbatim (enforced by
# .github/scripts/check-hardcoded-root.sh). resolve-root.sh explains the precedence
# and why the nt rewrite exists.
def agency_root(home):
    # MSYS-aware Python twin of hooks/lib/resolve-root.sh. That file documents
    # the precedence, why the /c/... rewrite is nt-only, and why this is inlined
    # at every call site instead of imported.
    root = os.environ.get('AGENCY_HOME') or os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(home, '.claude')
    if os.name == 'nt':
        m = re.fullmatch(r'/(?:cygdrive/)?([A-Za-z])(/.*)?', root)
        if m:
            root = m.group(1).upper() + ':' + (m.group(2) or '/')
    return root


ROOT = agency_root(HOME)
sys.path.insert(0, os.path.join(ROOT, "hooks", "lib"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "lib"))


def default_out():
    return os.path.join(ROOT, "state", "os", "cost-weekly.json")


def default_route_log():
    return os.environ.get("SKILL_ROUTE_LOG") or os.path.join(ROOT, "memory", "metrics", "skill-route.jsonl")


def jl(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if isinstance(r, dict):
                        yield r
                except Exception:
                    pass
    except Exception:
        return


def parse_ts(s):
    try:
        t = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def all_spawn_logs():
    import spawn_project
    primary = os.environ.get("SPAWN_LOG_FILE") or spawn_project.global_log(HOME)
    logs = [os.path.abspath(primary)] if os.path.isfile(primary) else []
    return logs + spawn_project.all_logs(primary, home=HOME)


def bucket():
    return {"usd": 0.0, "tokens": 0, "spawns": 0}


def add(b, usd, tok):
    b["usd"] = round(b["usd"] + usd, 6)
    b["tokens"] += tok
    b["spawns"] += 1


def build(logs, route_log, now, days):
    routes = {r["route_id"]: r for r in jl(route_log) if r.get("route_id")}
    starts, ends = {}, []
    for lg in logs:
        label = os.path.basename(os.path.dirname(os.path.dirname(lg)))
        for r in jl(lg):
            if r.get("event") == "spawn_start" and r.get("spawn_id"):
                r["_log"] = lg
                starts[r["spawn_id"]] = r
            elif r.get("event") == "spawn_end":
                r["_label"] = label
                ends.append(r)
    cut = now - datetime.timedelta(days=days)
    out = {k: collections.defaultdict(bucket) for k in ("by_skill", "by_agent_type", "by_project", "by_model")}
    tot = {"all": bucket(), "attributed": bucket(), "post_change": bucket(), "post_change_attributed": bucket(),
           "pre_change": bucket(), "pre_change_attributed": bucket(), "no_start_row": bucket()}
    cont = 0
    for e in ends:
        t = parse_ts(e.get("ts"))
        if not t or t < cut or t > now:
            continue
        usd, tok = float(e.get("cost_usd") or 0), int(e.get("tokens") or 0)
        s = starts.get(e.get("spawn_id"))
        cont += bool(e.get("continuation"))
        rid = (s or {}).get("jev_route_id") or ""
        att = bool(rid and rid in routes)
        post = bool(s and "jev_route_id" in s)
        proj = (s or {}).get("project") or e["_label"]
        skills = list((s or {}).get("skills") or []) or list(routes.get(rid, {}).get("skills") or []) or ["(none)"]
        add(tot["all"], usd, tok)
        if s is None:
            add(tot["no_start_row"], usd, tok)
        if att:
            add(tot["attributed"], usd, tok)
        grp = "post_change" if post else "pre_change"
        add(tot[grp], usd, tok)
        if att:
            add(tot[grp + "_attributed"], usd, tok)
        for sk in skills:  # cost split evenly across a spawn's skills so the column sums to the total
            b = out["by_skill"][sk]
            b["usd"] = round(b["usd"] + usd / len(skills), 6)
            b["tokens"] += tok // len(skills)
            b["spawns"] += 1
        add(out["by_agent_type"][e.get("agent_type") or (s or {}).get("subagent_type") or "unknown"], usd, tok)
        add(out["by_project"][proj], usd, tok)
        add(out["by_model"][e.get("model") or "unknown"], usd, tok)

    def pct(a, b):
        return round(100.0 * a["usd"] / b["usd"], 2) if b["usd"] else None
    return {
        "generated": now.isoformat(), "window_days": days, "logs_read": logs, "route_log": route_log,
        "unit_note": "usd = API-equivalent cost_usd from the transcript; tokens = raw tokens. Budget unit left open.",
        "totals": tot, "continuation_rows": cont,
        "attributed_pct": pct(tot["attributed"], tot["all"]),
        "attributed_pct_post_change": pct(tot["post_change_attributed"], tot["post_change"]),
        "attributed_pct_pre_change": pct(tot["pre_change_attributed"], tot["pre_change"]),
        **{k: dict(sorted(v.items(), key=lambda kv: -kv[1]["usd"])) for k, v in out.items()},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=default_out())
    ap.add_argument("--route-log", default=default_route_log())
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--now", default="")
    a = ap.parse_args(argv)
    try:
        now = parse_ts(a.now) if a.now else datetime.datetime.now(datetime.timezone.utc)
        rep = build(all_spawn_logs(), a.route_log, now, a.days)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=1)
        print("wrote %s total_usd=%s attributed_pct=%s post_change_pct=%s" % (
            a.out, rep["totals"]["all"]["usd"], rep["attributed_pct"], rep["attributed_pct_post_change"]))
    except Exception as ex:
        print("os-cost-report: %r" % ex, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
