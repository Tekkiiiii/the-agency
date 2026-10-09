#!/usr/bin/env python3
"""model-pin.py: the model pin + Exec cap policy for every subagent spawn.

Called by the spawn-ledger mod's `agent.spawn` hook (mods/spawn-ledger/hooks/register.ts) before the
ledger `start` row is written. Reads ONE JSON object on stdin:

  {subagent_type, model (string|null), fork, is_teammate, workflow,
   parent_spawn_id, parent_agent, tool_use_id, description, prompt}

and prints ONE JSON line:

  {action: pass|rewrite|deny, model: <string|null; null = strip the param so frontmatter decides>,
   old, new, reason, deny: "<message, deny only>"}

Why: the Agent tool's `model` param overrides an agent file's frontmatter
`model:`, so a spawner passing model:"opus" leaks Opus onto agents pinned to sonnet. Rules, in order:

  0. FAIL OPEN. Any exception -> pass + one best-effort `model_pin_error` row. Always exits 0.
     KILL SWITCH (pass, nothing logged): env MODEL_PIN_OFF=1, file $STATE/model-pin.off, or
     <root>/.hook-profile == minimal. The cap alone: env SPAWN_CAP_OFF=1 or $STATE/spawn-cap.off.
  1. fork / is_teammate / workflow -> untouched (cap too).
  2. NAMED subagent_type: the agent file's frontmatter `model:` is the single source of truth. A caller
     param that differs is stripped (model=null). No file / no model / inherit -> untouched.
  3. GENERAL-PURPOSE (general-purpose, claude, ""): model = map.categories[CAT] or map.default.
     An absent param counts as inherit (= the Opus parent), so it is rewritten too. Opt-in Opus
     escalation via a `MODEL-ESCALATE: opus - <reason>` line, OFF by default (map.escalation).
  4. EXEC CAP: at most map.exec_cap.max general-purpose/task-executor spawns running per ROOT PD,
     counted across the PD's whole tree (its coords, mini-coords and direct Execs; coords never count).
     Root = the nearest ancestor whose subagent_type ends "-pd" or is "pd-coordinator", found by walking
     parent_spawn_id up through the spawn_start rows (key "pd:<PD subagent_type>", so a respawned PD of the
     same project shares one budget). Chain fully resolved with no PD (main -> coord -> exec) = exempt.
     Chain broken (a parent has no spawn_start row) = FAIL OPEN: pass + one model_pin_error row; never a
     per-parent count. Count + reserve (state/spawn-slots.jsonl, keyed by root) under flock so parallel
     spawns in one message cannot all slip through.
  5. LOGGING: `model_override` / `spawn_denied` rows go to the spawn log (same file ledger.py writes).

Config: exec-model-map.json next to this file (override: env MODEL_PIN_MAP). Test overrides:
SPAWN_LOG_FILE, MODEL_PIN_MAP, MODEL_PIN_AGENTS_DIR, MODEL_PIN_STATE_DIR, MODEL_PIN_NOW (epoch),
MODEL_PIN_HOME (replaces $HOME when the root is derived: <root> = AGENCY_HOME, else CLAUDE_CONFIG_DIR, else
$MODEL_PIN_HOME/.claude; the profile is <root>/.hook-profile),
MODEL_PIN_GLOBAL_LOG (second log scanned by the cap; empty = none),
MODEL_PIN_TEST_RACE_DELAY (seconds slept between count and reserve; lets the race test prove the lock).
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import fcntl  # POSIX only; on Windows the cap runs without the lock (parallel spawns may over-count)
except ImportError:
    fcntl = None

HOME = os.environ.get("MODEL_PIN_HOME") or os.path.expanduser("~")


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
HERE = os.path.dirname(os.path.abspath(__file__))
GP_TYPES = ("general-purpose", "claude", "")
RESERVATION_TTL_SEC = 60
LOG_TAIL_BYTES = 8 * 1024 * 1024

BUILTIN_MAP = {"default": "sonnet", "categories": {}}
CAP_DEFAULTS = {"enabled": True, "max": 5, "types": ["general-purpose", "task-executor"],
                "include_root": False, "stale_after_sec": 7200}
ESC_DEFAULTS = {"enabled": False, "allowed": ["opus"]}


# ---- environment ----------------------------------------------------------

def now_epoch():
    v = os.environ.get("MODEL_PIN_NOW", "")
    try:
        return float(v) if v else time.time()
    except ValueError:
        return time.time()


def iso(epoch):
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def state_dir():
    return os.environ.get("MODEL_PIN_STATE_DIR") or os.path.join(ROOT, "state")


def agents_dir():
    return os.environ.get("MODEL_PIN_AGENTS_DIR") or os.path.join(ROOT, "agents")


def map_path():
    return os.environ.get("MODEL_PIN_MAP") or os.path.join(HERE, "exec-model-map.json")


def resolve_log_file():
    """Copy of mods/spawn-ledger/bin/ledger.py resolve_log_file(): SPAWN_LOG_FILE, else the project
    log picked by longest-prefix match of the cwd against medium-term.md, else logs/spawns.jsonl.
    Same cwd as ledger.py (both run via $.process.run), so the cap reads the file ledger.py writes."""
    override = os.environ.get("SPAWN_LOG_FILE", "")
    if override:
        return override
    fallback = os.path.join(ROOT, "logs", "spawns.jsonl")
    medium_term = os.path.join(ROOT, "memory", "medium-term.md")
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    if not os.path.exists(medium_term):
        return fallback
    best_len, best_path = 0, ""
    try:
        with open(medium_term) as f:
            for line in f:
                m = re.match(r"^\|[^|]+\|\s*`([^`]+)`", line)
                if not m:
                    continue
                raw = m.group(1).replace("~", HOME).rstrip("/")
                root = (raw[:-7] if raw.endswith("/memory") else raw).rstrip("/")
                if root and cwd.startswith(root) and len(root) > best_len:
                    best_len, best_path = len(root), root
    except Exception:
        pass
    if best_path:
        return os.path.join(best_path, "memory", "spawns.jsonl")
    return fallback


def global_log_file():
    if "MODEL_PIN_GLOBAL_LOG" in os.environ:
        return os.environ["MODEL_PIN_GLOBAL_LOG"]
    return os.path.join(ROOT, "logs", "spawns.jsonl")


def append_row(row):
    """Best-effort single-write append to the spawn log."""
    try:
        path = resolve_log_file()
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


# ---- kill switches --------------------------------------------------------

def kill_switch():
    if os.environ.get("MODEL_PIN_OFF") == "1":
        return "env MODEL_PIN_OFF"
    if os.path.exists(os.path.join(state_dir(), "model-pin.off")):
        return "flag file model-pin.off"
    try:
        with open(os.path.join(ROOT, ".hook-profile")) as f:
            if f.read().strip() == "minimal":
                return "hook-profile minimal"
    except Exception:
        pass
    return ""


def cap_killed():
    return os.environ.get("SPAWN_CAP_OFF") == "1" or os.path.exists(os.path.join(state_dir(), "spawn-cap.off"))


# ---- map ------------------------------------------------------------------

def load_map():
    """Missing file -> built-in default. Unreadable/corrupt/wrong shape -> raises (caller fails open)."""
    try:
        with open(map_path()) as f:
            text = f.read()
    except FileNotFoundError:
        return dict(BUILTIN_MAP)
    m = json.loads(text)
    if not isinstance(m, dict):
        raise ValueError("map is not a JSON object")
    cats = m.get("categories", {})
    if not isinstance(cats, dict) or not all(isinstance(v, str) for v in cats.values()):
        raise ValueError("map.categories must be an object of strings")
    if "default" in m and not isinstance(m["default"], str):
        raise ValueError("map.default must be a string")
    for key in ("escalation", "exec_cap"):
        if key in m and not isinstance(m[key], dict):
            raise ValueError("map.%s must be an object" % key)
    return m


# ---- model helpers --------------------------------------------------------

def norm(model):
    """Compare key: case-insensitive, trailing [..] context suffix ignored."""
    return re.sub(r"\[[^\]]*\]\s*$", "", (model or "").strip()).lower()


FENCED = re.compile(r"^[ \t]*(```|~~~)[\s\S]*?^[ \t]*\1[^\n]*$", re.M)


def strip_fences(text):
    return FENCED.sub("", text or "")


def agent_frontmatter_model(subagent_type):
    """Frontmatter `model:` of the agent file whose `name:` is subagent_type (the matching approach of
    ledger.py agent_def_model, but a sorted walk so duplicates resolve deterministically).
    Returns "" when there is no file, no model, or the model is `inherit`."""
    try:
        for root, dirs, files in os.walk(agents_dir()):
            dirs.sort()
            for fn in sorted(files):
                if not fn.endswith(".md"):
                    continue
                with open(os.path.join(root, fn), errors="ignore") as af:
                    head = af.read(4000)
                if not head.startswith("---"):
                    continue
                fm = head.split("---", 2)[1] if head.count("---") >= 2 else ""
                nm = re.search(r"^name:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
                if nm and nm.group(1).strip() == subagent_type:
                    mm = re.search(r"^model:\s*[\"']?([^\s\"']+)", fm, re.M)
                    val = mm.group(1) if mm else ""
                    return "" if val.lower() == "inherit" else val
    except Exception:
        pass
    return ""


CAT_INLINE = re.compile(r"\[category:\s*([A-Za-z0-9_-]+)\s*\]", re.I)
CAT_LINE = re.compile(r"^[ \t]*MODEL-CATEGORY:[ \t]*([A-Za-z0-9_-]+)[ \t]*$", re.M)
ESC_LINE = re.compile(r"^[ \t]*MODEL-ESCALATE:[ \t]*([A-Za-z0-9_.\[\]-]+)[ \t]+[-—–][ \t]+(\S.*?)[ \t]*$", re.M)


def find_category(description, prompt):
    text = strip_fences(description) + "\n" + strip_fences(prompt)
    m = CAT_INLINE.search(text) or CAT_LINE.search(text)
    return m.group(1).lower() if m else ""


def find_escalation(prompt):
    m = ESC_LINE.search(strip_fences(prompt))
    return (m.group(1).strip().lower(), m.group(2).strip()) if m else None


def decide_model(d, m):
    """-> (action, model, old, new, reason). model None on rewrite = strip the param."""
    subagent_type = d.get("subagent_type") or ""
    param = d.get("model") or None
    if subagent_type not in GP_TYPES:
        fm = agent_frontmatter_model(subagent_type)
        if fm and param and norm(param) != norm(fm):
            return "rewrite", None, param, fm, "named_frontmatter_wins"
        return "pass", param, param, None, ""
    cats = m.get("categories") or {}
    cat = find_category(d.get("description") or "", d.get("prompt") or "")
    desired = cats.get(cat) or m.get("default") or "sonnet"
    reason = "gp_category_map"
    esc = dict(ESC_DEFAULTS, **(m.get("escalation") or {}))
    marker = find_escalation(d.get("prompt") or "")
    if marker:
        em, why = marker
        allowed = [norm(a) for a in (esc.get("allowed") or [])]
        if esc.get("enabled") is True and norm(em) in allowed:
            desired, reason = em, "escalation_marker:" + why
        elif esc.get("enabled") is not True:
            reason += " (escalation marker ignored: disabled)"
    if param and norm(param) == norm(desired):
        return "pass", param, param, None, reason if reason.startswith("escalation") else ""
    return "rewrite", desired, param, desired, reason


# ---- Exec cap ---------------------------------------------------------------

def parse_ts(s):
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.astimezone()
        return dt.timestamp()
    except Exception:
        return None


def read_log_rows(path):
    """Rows of one spawn log, tail-capped (an old start whose end we cannot see is stale anyway)."""
    rows = []
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > LOG_TAIL_BYTES:
                f.seek(size - LOG_TAIL_BYTES)
                f.readline()  # drop the partial first line
            data = f.read().decode("utf-8", errors="ignore")
    except Exception:
        return rows
    for line in data.splitlines():
        line = line.strip()
        if not line or "spawn_" not in line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows


def norm_type(t):
    return "general-purpose" if (t or "") in GP_TYPES else t


MAX_ANCESTRY_DEPTH = 16
ROOT_KEY_EMPTY_PARENT = "root:"  # include_root: spawns of the main session (no parent) share this key


def is_pd(t):
    t = t or ""
    return t.endswith("-pd") or t == "pd-coordinator"


class Ancestry:
    """Resolves the root PD key of a spawn from spawn_start rows (indexed by spawn_id), memoized.
    root_key(row) -> ("pd", "pd:<type>") | ("none", None) chain fully resolved, no PD above
                   | ("unresolved", <parent_spawn_id with no row>) broken chain / cycle / too deep."""

    def __init__(self, rows):
        self.idx = {}
        for r in rows:
            if r.get("event") == "spawn_start" and r.get("spawn_id"):
                self.idx[r["spawn_id"]] = r
        self.memo = {}

    def root_key(self, row, include_root=False):
        if is_pd(row.get("parent_agent")):
            return "pd", "pd:" + row["parent_agent"]
        pid = row.get("parent_spawn_id") or ""
        if not pid:
            return ("pd", ROOT_KEY_EMPTY_PARENT) if include_root else ("none", None)
        return self._walk(pid)

    def _walk(self, pid):
        """Resolution of the ancestry starting AT spawn pid (that row and everything above it)."""
        chain, seen, res = [], set(), None
        cur = pid
        while res is None:
            if cur in self.memo:
                res = self.memo[cur]
            elif cur in seen or len(chain) >= MAX_ANCESTRY_DEPTH:
                res = ("unresolved", cur)
            else:
                row = self.idx.get(cur)
                if row is None:
                    res = ("unresolved", cur)
                elif is_pd(row.get("subagent_type")):
                    res = ("pd", "pd:" + row["subagent_type"])
                elif is_pd(row.get("parent_agent")):
                    res = ("pd", "pd:" + row["parent_agent"])
                elif not (row.get("parent_spawn_id") or ""):
                    res = ("none", None)
                else:
                    seen.add(cur)
                    chain.append(cur)
                    cur = row["parent_spawn_id"]
        for c in chain:
            self.memo[c] = res
        self.memo[pid] = res
        return res


def count_running(rows, root, types, stale, now, anc=None, include_root=False):
    """spawn_start rows under this root PD, a capped type, within the stale window, with no spawn_end.
    Ended = spawn_end with the same spawn_id (ABANDONED sweep rows included), OR whose agent_id is the
    agent_id of the spawn_launched row of that spawn (spawn_end rows sometimes carry spawn_id "").
    Also ended = spawn_end with the start's tool_use_id."""
    ended_sid, ended_agent, ended_tuid = set(), set(), set()
    agent_by_sid, agent_by_tuid = {}, {}
    start_tuids = set()
    starts = {}
    for r in rows:
        ev = r.get("event")
        if ev == "spawn_start":
            if r.get("tool_use_id"):
                start_tuids.add(r["tool_use_id"])
            if r.get("spawn_id"):
                starts[r["spawn_id"]] = r
        elif ev == "spawn_end":
            if r.get("spawn_id"):
                ended_sid.add(r["spawn_id"])
            if r.get("agent_id"):
                ended_agent.add(r["agent_id"])
            if r.get("tool_use_id"):
                ended_tuid.add(r["tool_use_id"])
        elif ev == "spawn_launched" and r.get("agent_id"):
            if r.get("spawn_id"):
                agent_by_sid[r["spawn_id"]] = r["agent_id"]
            if r.get("tool_use_id"):
                agent_by_tuid[r["tool_use_id"]] = r["agent_id"]
    anc = anc or Ancestry(rows)
    running = 0
    for sid, r in starts.items():
        if norm_type(r.get("subagent_type") or "") not in types:
            continue
        kind, key = anc.root_key(r, include_root)
        if kind != "pd" or key != root:
            continue
        ts = parse_ts(r.get("ts"))
        if ts is None or now - ts > stale:
            continue
        tuid = r.get("tool_use_id") or ""
        agent = agent_by_sid.get(sid) or agent_by_tuid.get(tuid)
        if sid in ended_sid or (tuid and tuid in ended_tuid) or (agent and agent in ended_agent):
            continue
        running += 1
    return running, start_tuids


def cap_check(cap, parent, parent_agent, tuid, now):
    """-> (status, denied, total_running_plus_reserved, root). status: "ok" (root PD found and counted),
    "exempt" (chain fully resolved, no PD) or "unresolved" (broken chain; root = the missing spawn_id).
    Count + reserve atomically under flock; exempt/unresolved spawns reserve nothing."""
    max_n = int(cap.get("max", 5))
    stale = float(cap.get("stale_after_sec", 7200))
    types = set(norm_type(t) for t in (cap.get("types") or []))
    include_root = cap.get("include_root") is True
    sd = state_dir()
    os.makedirs(sd, exist_ok=True)
    slots = os.path.join(sd, "spawn-slots.jsonl")
    with open(os.path.join(sd, "spawn-slots.lock"), "a") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            log = resolve_log_file()
            rows = read_log_rows(log)
            g = global_log_file()
            if g and os.path.realpath(g) != os.path.realpath(log):
                rows += read_log_rows(g)
            anc = Ancestry(rows)
            kind, root = anc.root_key({"parent_spawn_id": parent, "parent_agent": parent_agent}, include_root)
            if kind == "none":
                return "exempt", False, 0, None
            if kind == "unresolved":
                return "unresolved", False, 0, root
            running, start_tuids = count_running(rows, root, types, stale, now, anc, include_root)
            fresh = []
            try:
                with open(slots) as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                        except Exception:
                            continue
                        if isinstance(r, dict) and now - float(r.get("ts", 0)) < RESERVATION_TTL_SEC:
                            fresh.append(r)
            except FileNotFoundError:
                pass
            held, seen = 0, set()
            for r in fresh:
                t = r.get("tool_use_id") or ""
                if r.get("root") != root or (t and t in start_tuids) or (tuid and t == tuid):
                    continue  # (old-format lines have no "root": ignored, expire after the TTL)
                if t:
                    if t in seen:
                        continue
                    seen.add(t)
                held += 1
            total = running + held
            _race_delay = os.environ.get("MODEL_PIN_TEST_RACE_DELAY")  # test hook: widen the count->reserve window
            if _race_delay:
                time.sleep(float(_race_delay))
            if total >= max_n:
                keep = fresh
                denied = True
            else:
                keep = [r for r in fresh if not (tuid and r.get("tool_use_id") == tuid)]
                keep.append({"root": root, "tool_use_id": tuid, "ts": now})
                denied = False
            with open(slots, "w") as f:
                for r in keep:
                    f.write(json.dumps(r) + "\n")
            return "ok", denied, total, root
        finally:
            if fcntl:
                fcntl.flock(lock, fcntl.LOCK_UN)


def cap_message(n, max_n, root):
    pd = root[3:] if (root or "").startswith("pd:") else (root or "?")
    return ("[spawn-cap] %d Execs already running under PD %s tree (cap %d, Exec cap policy: max %d Execs per PD "
            "across all its coords). Please wait for a slot - a completion notification arrives on its own - "
            "then spawn again, or merge tasks. Do not retry in a loop." % (n, pd, max_n, max_n))


# ---- main -----------------------------------------------------------------

def result(action="pass", model=None, old=None, new=None, reason="", deny=None):
    out = {"action": action, "model": model, "old": old, "new": new, "reason": reason}
    if deny is not None:
        out["deny"] = deny
    return out


def decide(raw):
    ks = kill_switch()
    if ks:
        return result(reason="kill switch: " + ks)
    d = json.loads(raw)
    if not isinstance(d, dict):
        raise ValueError("stdin is not a JSON object")
    param = d.get("model") or None
    if d.get("fork") or d.get("is_teammate") or d.get("workflow"):
        return result(model=param, old=param, reason="untouched: fork/teammate/workflow")
    m = load_map()
    action, model, old, new, reason = decide_model(d, m)
    out = result(action, model, old, new, reason)

    cap = dict(CAP_DEFAULTS, **(m.get("exec_cap") or {}))
    parent = d.get("parent_spawn_id") or ""
    parent_agent = d.get("parent_agent") or ""
    subagent_type = d.get("subagent_type") or ""
    tuid = d.get("tool_use_id") or ""
    types = set(norm_type(t) for t in (cap.get("types") or []))
    if (cap.get("enabled") is True and not cap_killed() and norm_type(subagent_type) in types
            and (parent or is_pd(parent_agent) or cap.get("include_root") is True)):
        status, denied, total, root = "ok", False, 0, None
        try:
            status, denied, total, root = cap_check(cap, parent, parent_agent, tuid, now_epoch())
        except Exception as e:  # the cap fails open on its own; the rewrite below still applies
            denied, total = False, 0
            append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "error": "cap: %s: %s" % (type(e).__name__, e)})
        if status == "unresolved":  # exactly one best-effort row per call; pass, never a per-parent count
            append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "parent_spawn_id": parent,
                        "error": "cap: ancestry unresolved (no spawn_start row for %s); no PD root found, "
                                 "cap skipped (fail open)" % root})
        if denied:
            max_n = int(cap.get("max", 5))
            append_row({"event": "spawn_denied", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "parent_spawn_id": parent, "root": root,
                        "running": total, "cap": max_n, "reason": "spawn_cap"})
            return result("deny", None, param, None, "spawn_cap", cap_message(total, max_n, root))

    if action == "rewrite":
        append_row({"event": "model_override", "ts": iso(now_epoch()), "tool_use_id": tuid,
                    "subagent_type": subagent_type, "old": old, "new": new, "reason": reason,
                    "parent_spawn_id": parent})
    return out


def main():
    raw = ""
    try:
        raw = sys.stdin.read()
        out = decide(raw)
    except BaseException as e:  # fail open, whatever it was
        out = result(reason="error: %s: %s" % (type(e).__name__, e))
        try:
            ctx = json.loads(raw) if raw.strip() else {}
            ctx = ctx if isinstance(ctx, dict) else {}
        except Exception:
            ctx = {}
        append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": ctx.get("tool_use_id", ""),
                    "subagent_type": ctx.get("subagent_type", ""), "error": "%s: %s" % (type(e).__name__, e)})
    try:
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
