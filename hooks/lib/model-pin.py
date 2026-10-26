#!/usr/bin/env python3
"""model-pin.py: the model pin + Exec cap policy for every subagent spawn.

Called by the spawn-ledger mod's `agent.spawn` hook (mods/spawn-ledger/hooks/register.ts) before the
ledger `start` row is written. Reads ONE JSON object on stdin:

  {subagent_type, model (string|null), fork, is_teammate, workflow,
   parent_spawn_id, parent_agent, tool_use_id, description, prompt}

and prints ONE JSON line:

  {action: pass|rewrite|deny, model: <string|null; null = strip the param so frontmatter decides>,
   old, new, reason, effort: <low|medium|high|xhigh|max|null>, effort_category: <string|null>,
   deny: "<message, deny only>"}

(`effort` / `effort_category` are on every non-deny result, null when no effort is decided; a deny carries neither.)

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
     escalation via a `MODEL-ESCALATE: opus - <reason>` line; code default OFF (ESC_DEFAULTS), a map enables it (map.escalation).
  4. EXEC CAP: at most map.exec_cap.max general-purpose/task-executor spawns running per ROOT PD,
     counted across the PD's whole tree (its coords, mini-coords and direct Execs; coords never count).
     Root = the nearest ancestor whose subagent_type ends "-pd" or is "pd-coordinator", found by walking
     parent_spawn_id up through the spawn_start rows (key "pd:<PD subagent_type>", so a respawned PD of the
     same project shares one budget). Chain fully resolved with no PD (main -> coord -> exec) = exempt.
     Chain broken (a parent has no spawn_start row) = FAIL OPEN: pass + one model_pin_error row; never a
     per-parent count. Count + reserve (state/spawn-slots.jsonl, keyed by root) under flock so parallel
     spawns in one message cannot all slip through.
  5. LOGGING: `model_override` / `spawn_denied` rows go to the spawn log ledger.py picks for the same spawn
     (hooks/lib/spawn_project.py: Project: line, {slug}-pd parent/type, cwd, global). The cap reads ALL known logs
     (the PD tree's start rows split over project + global logs). spawn_project.py missing -> global log only +
     one model_pin_error row (fail open).

EFFORT POLICY (Owner ruling 2026-10-15; the `effort` section of exec-model-map.json is the single source of truth).
The Agent tool cannot set `effort` at agent.spawn, so this hook only DECIDES it; the spawn-ledger `turn.step` hook applies
it. decide_effort(), first match wins, fork/teammate/workflow excepted (no effort + one `effort_skipped` row):
  a. PD (type ends "-pd" or == pd-coordinator)          -> category `pd`.
  b. type listed in effort.agents (exact match)         -> that category (reason `agent_table`).
  c. any other named type                               -> no effort (Council seats, caveman:*, built-ins untouched).
  d. general-purpose: a `MODEL-CATEGORY:` marker listed in effort.marker_categories -> that category; else the Jev route
     cache entry named by the prompt's `Jev[r=<id>]` line, read DIRECTLY from <SKILL_ROUTE_STATE_DIR or
     <root>/state/skill-route>/jev-route-cache/<id>.json (48h TTL; no router import, no Jev call): gate pass ->
     domain family (effort.domains): visual -> `visual`; content -> `content_vi` when cache lang == vi or domain ==
     writing-vi else `content_en`; coding -> `coding_complex` when a complexity signal fires (effort.complexity: domain,
     skill in the cache or the prompt's `Skills:` line, marker word in description+prompt outside code fences) else
     `coding_routine`; other/unknown -> `other`. No Jev line / no usable cache entry / jev_down / gate != pass ->
     effort.fallback_category (`other`).
  The value is effort.categories[category] and ALWAYS wins over the caller's `effort` and the agent frontmatter.
  Ledger rows (same log as model_override): `effort_override` (value differs from the agent file's `effort:`, or that is
  unknown), `effort_policy` (already equal), `effort_skipped` (fork/teammate/workflow). A bad `effort` section or any
  error inside the effort step -> no effort + exactly one `model_pin_error` row prefixed `effort: `; the model decision
  and the cap are never affected (fail open).
  Effort-only kill switch: env EFFORT_POLICY_OFF=1, file $STATE/effort-policy.off, or effort.enabled == false (the model
  pin keeps working). The model-pin kill switches above also switch effort off.

SPAWN_LOG_FILE, SPAWN_LEDGER_EXTRA_LOGS (the only extra logs the cap reads when SPAWN_LOG_FILE is set), SPAWN_MEDIUM_TERM, SKILL_ROUTE_STATE_DIR (Jev route cache base), MODEL_PIN_MAP, MODEL_PIN_AGENTS_DIR, MODEL_PIN_STATE_DIR, MODEL_PIN_NOW (epoch),

Config: exec-model-map.json next to this file (override: env MODEL_PIN_MAP). Test overrides:
SPAWN_LOG_FILE, SPAWN_LEDGER_EXTRA_LOGS (the only extra logs the cap reads when SPAWN_LOG_FILE is set), SPAWN_MEDIUM_TERM, SKILL_ROUTE_STATE_DIR (Jev route cache base), MODEL_PIN_MAP, MODEL_PIN_AGENTS_DIR, MODEL_PIN_STATE_DIR, MODEL_PIN_NOW (epoch),
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

try:  # ponytail: win32 has no fcntl; lock via msvcrt there, else best-effort (no lock)
    import fcntl
except ImportError:
    fcntl = None
try:
    import msvcrt
except ImportError:
    msvcrt = None

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
sys.path.insert(0, HERE)
try:
    import spawn_project  # shared with mods/spawn-ledger/bin/ledger.py: one project -> spawns.jsonl resolution
    SPAWN_PROJECT_ERROR = ""
except Exception as _e:  # fail open: global log only (cap still reads the global log); decide() logs one error row
    spawn_project = None
    SPAWN_PROJECT_ERROR = "%s: %s" % (type(_e).__name__, _e)
GP_TYPES = ("general-purpose", "claude", "")
RESERVATION_TTL_SEC = 60
LOG_TAIL_BYTES = 8 * 1024 * 1024

BUILTIN_MAP = {"default": "sonnet", "categories": {}}
CAP_DEFAULTS = {"enabled": True, "max": 5, "types": ["general-purpose", "task-executor"],
                "include_root": False, "stale_after_sec": 7200}
ESC_DEFAULTS = {"enabled": False, "allowed": ["opus"]}
EFFORT_VALUES = ("low", "medium", "high", "xhigh", "max")
EFFORT_FAMILIES = ("visual", "content", "coding", "other")
JEV_CACHE_TTL_SEC = 48 * 3600  # same as scripts/jev_spawn.py CACHE_TTL_SECONDS


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


def resolve_log_file(d=None):
    """The spawns.jsonl ledger.py would write this spawn to (hooks/lib/spawn_project.py, shared): SPAWN_LOG_FILE,
    else the project from the payload hint d (Project: line in the prompt, parent_agent / subagent_type {slug}-pd),
    else CLAUDE_PROJECT_DIR/cwd longest-prefix, else logs/spawns.jsonl."""
    override = os.environ.get("SPAWN_LOG_FILE", "")
    if override:
        return override
    if spawn_project is not None:
        try:
            return spawn_project.resolve_log_file(d if isinstance(d, dict) else None, home=HOME)
        except Exception:
            pass
    return os.path.join(ROOT, "logs", "spawns.jsonl")


def cap_logs(d=None):
    """Every spawn log the cap reads: the resolved log, all other known logs (a PD tree's start rows split over
    project + global logs; the parent chain only resolves if all are read), and MODEL_PIN_GLOBAL_LOG. Deduped by realpath."""
    paths = [resolve_log_file(d)]
    if spawn_project is not None:
        try:
            paths += spawn_project.all_logs(paths[0], home=HOME)
        except Exception:
            pass
    g = global_log_file()
    if g:
        paths.append(g)
    seen, out = set(), []
    for p in paths:
        try:
            k = os.path.realpath(p)
        except Exception:
            k = p
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def global_log_file():
    if "MODEL_PIN_GLOBAL_LOG" in os.environ:
        return os.environ["MODEL_PIN_GLOBAL_LOG"]
    return os.path.join(ROOT, "logs", "spawns.jsonl")


def append_row(row, d=None):
    """Best-effort single-write append to the spawn log; d = the spawn payload, so the row follows the same log
    ledger.py picks for that spawn."""
    try:
        path = resolve_log_file(d)
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
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
        with open(os.path.join(ROOT, ".hook-profile"), encoding="utf-8") as f:
            if f.read().strip() == "minimal":
                return "hook-profile minimal"
    except Exception:
        pass
    return ""


def effort_killed():
    return os.environ.get("EFFORT_POLICY_OFF") == "1" or os.path.exists(os.path.join(state_dir(), "effort-policy.off"))


def cap_killed():
    return os.environ.get("SPAWN_CAP_OFF") == "1" or os.path.exists(os.path.join(state_dir(), "spawn-cap.off"))


# ---- map ------------------------------------------------------------------

def load_map():
    """Missing file -> built-in default. Unreadable/corrupt/wrong shape -> raises (caller fails open)."""
    try:
        with open(map_path(), encoding="utf-8") as f:
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


def agent_frontmatter(subagent_type):
    """Frontmatter text of the agent file whose `name:` is subagent_type (the matching approach of ledger.py
    agent_def_model, but a sorted walk so duplicates resolve deterministically). "" when there is no such file."""
    try:
        for root, dirs, files in os.walk(agents_dir()):
            dirs.sort()
            for fn in sorted(files):
                if not fn.endswith(".md"):
                    continue
                with open(os.path.join(root, fn), encoding="utf-8", errors="ignore") as af:
                    head = af.read(4000)
                if not head.startswith("---"):
                    continue
                fm = head.split("---", 2)[1] if head.count("---") >= 2 else ""
                nm = re.search(r"^name:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
                if nm and nm.group(1).strip() == subagent_type:
                    return fm
    except Exception:
        pass
    return ""


def agent_frontmatter_model(subagent_type):
    """Frontmatter `model:` of the named agent file. Returns "" when there is no file, no model, or the model
    is `inherit`."""
    mm = re.search(r"^model:\s*[\"']?([^\s\"']+)", agent_frontmatter(subagent_type), re.M)
    val = mm.group(1) if mm else ""
    return "" if val.lower() == "inherit" else val


def agent_frontmatter_effort(subagent_type):
    """Frontmatter `effort:` of the named agent file, lower-cased; None when there is no file or no line."""
    mm = re.search(r"^effort:\s*[\"']?([^\s\"']+)", agent_frontmatter(subagent_type), re.M)
    return mm.group(1).lower() if mm else None


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


# ---- effort policy --------------------------------------------------------

JEV_ID = re.compile(r"Jev\[r=([0-9a-f]{8})\]")
SKILLS_LINE = re.compile(r"^[ \t]*Skills:[ \t]*(.+)$", re.M)
SKILL_TOKEN = re.compile(r"/([A-Za-z0-9][A-Za-z0-9_.:-]*)")


class EffortSkip(Exception):
    """Raised inside the effort step to mean "no effort for this spawn" with a reason (not an error)."""


def validate_effort(cfg):
    """Raises ValueError on a malformed `effort` section (caller fails open with one error row)."""
    if not isinstance(cfg, dict):
        raise ValueError("map.effort must be an object")
    cats = cfg.get("categories")
    if not isinstance(cats, dict) or not cats:
        raise ValueError("effort.categories must be a non-empty object")
    for k, v in cats.items():
        if v not in EFFORT_VALUES:
            raise ValueError("effort.categories.%s=%r is not one of %s" % (k, v, "/".join(EFFORT_VALUES)))
    if cfg.get("fallback_category") not in cats:
        raise ValueError("effort.fallback_category %r is not a category" % (cfg.get("fallback_category"),))
    for key in ("agents", "marker_categories"):
        tbl = cfg.get(key, {})
        if not isinstance(tbl, dict) or any(v not in cats for v in tbl.values()):
            raise ValueError("effort.%s must map to known categories" % key)
    dom = cfg.get("domains", {})
    if not isinstance(dom, dict) or any(v not in EFFORT_FAMILIES for v in dom.values()):
        raise ValueError("effort.domains must map to one of %s" % "/".join(EFFORT_FAMILIES))
    cx = cfg.get("complexity", {})
    if not isinstance(cx, dict) or any(not isinstance(cx.get(k, []), list) or
                                       any(not isinstance(x, str) for x in cx.get(k, []))
                                       for k in ("domains", "skills", "markers")):
        raise ValueError("effort.complexity.{domains,skills,markers} must be lists of strings")


def jev_cache_entry(route_id):
    """The Jev route cache entry for route_id, read directly from the JSON file (scripts/jev_spawn.py layout, no
    import). None when missing / unreadable / not an object / older than the 48h TTL."""
    base = os.environ.get("SKILL_ROUTE_STATE_DIR") or os.path.join(ROOT, "state", "skill-route")
    path = os.path.join(base, "jev-route-cache", route_id + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        if not isinstance(entry, dict):
            return None
        try:
            ts = float(entry.get("ts"))
        except (TypeError, ValueError):
            ts = now_epoch()
        try:
            mt = os.path.getmtime(path)
        except OSError:
            mt = now_epoch()
        if now_epoch() - min(ts, mt) > JEV_CACHE_TTL_SEC:
            return None
        return entry
    except Exception:
        return None


def coding_signal(cfg, d, entry):
    """First complexity signal that fires for a coding spawn, as 'domain:x' / 'skill:x' / 'marker:x', else ''."""
    cx = cfg.get("complexity") or {}
    if entry.get("domain") in (cx.get("domains") or []):
        return "domain:%s" % entry.get("domain")
    prompt = d.get("prompt") or ""
    named = set(str(s) for s in (entry.get("skills") or []))
    for line in SKILLS_LINE.findall(strip_fences(prompt)):
        named.update(SKILL_TOKEN.findall(line))
    for sk in (cx.get("skills") or []):
        if sk in named:
            return "skill:%s" % sk
    text = strip_fences(d.get("description") or "") + "\n" + strip_fences(prompt)
    for mk in (cx.get("markers") or []):
        if re.search(r"\b" + re.escape(mk), text, re.I):
            return "marker:%s" % mk
    return ""


def decide_effort(d, m):
    """-> {category, value, reason, old} or None (no effort for this spawn). Order and reasons: see the module
    docstring. Raises on a bad config (caller fails open)."""
    cfg = m.get("effort")
    if cfg is None or (isinstance(cfg, dict) and cfg.get("enabled") is False):
        return None
    validate_effort(cfg)
    st = d.get("subagent_type") or ""
    cats = cfg["categories"]

    def out(cat, reason):
        old = agent_frontmatter_effort(st) if st not in GP_TYPES else None
        return {"category": cat, "value": cats[cat], "reason": reason, "old": old}

    if is_pd(st):
        return out("pd", "pd")
    agents = cfg.get("agents") or {}
    if st in agents:
        return out(agents[st], "agent_table")
    if st not in GP_TYPES:
        return None  # named_unlisted: Council seats, caveman:*, built-ins stay untouched
    mk = find_category(d.get("description") or "", d.get("prompt") or "")
    mcats = cfg.get("marker_categories") or {}
    if mk in mcats:
        return out(mcats[mk], "marker:" + mk)
    fb = cfg["fallback_category"]
    mid = JEV_ID.search(d.get("prompt") or "")
    if not mid:
        return out(fb, "jev_unavailable")
    entry = jev_cache_entry(mid.group(1))
    if entry is None:
        return out(fb, "jev_no_route")
    if entry.get("jev_down") is True:
        return out(fb, "jev_unavailable")
    if entry.get("gate") != "pass":
        return out(fb, "jev_low_confidence")
    domain = entry.get("domain") or ""
    family = (cfg.get("domains") or {}).get(domain, "other")
    if family == "visual":
        return out("visual", "domain:" + domain)
    if family == "content":
        if str(entry.get("lang") or "").lower() == "vi":
            return out("content_vi", "lang:vi")
        if domain == "writing-vi":
            return out("content_vi", "domain:writing-vi")
        return out("content_en", "domain:" + domain)
    if family == "coding":
        sig = coding_signal(cfg, d, entry)
        if sig:
            return out("coding_complex", "coding_complex:" + sig)
        return out("coding_routine", "coding_routine")
    return out("other", "domain:" + domain if domain else "other")


def effort_step(d, m, tuid, parent, subagent_type):
    """-> (value, category). Runs the whole effort step incl. its ledger rows; never raises (one `effort: ` error
    row instead). m may be None (only fork/teammate/workflow spawns call it without having loaded the map)."""
    try:
        if effort_killed():
            return None, None
        if m is None:
            try:
                m = load_map()
            except Exception:
                return None, None  # untouched-path spawn: a broken map is the model path's business, not ours
        cfg = m.get("effort")
        if cfg is None or (isinstance(cfg, dict) and cfg.get("enabled") is False):
            return None, None
        why = ("fork ignores effort" if d.get("fork") else "teammate" if d.get("is_teammate")
               else "workflow" if d.get("workflow") else "")
        if why:
            validate_effort(cfg)
            append_row({"event": "effort_skipped", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "reason": why}, d)
            return None, None
        r = decide_effort(d, m)
        if r is None:
            return None, None
        append_row({"event": "effort_policy" if r["old"] == r["value"] else "effort_override",
                    "ts": iso(now_epoch()), "tool_use_id": tuid, "subagent_type": subagent_type,
                    "category": r["category"], "old": r["old"], "new": r["value"], "reason": r["reason"],
                    "parent_spawn_id": parent}, d)
        return r["value"], r["category"]
    except Exception as e:
        append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": tuid,
                    "subagent_type": subagent_type, "error": "effort: %s: %s" % (type(e).__name__, e)}, d)
        return None, None


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


def _lock(fh):
    """Exclusive lock on fh. POSIX: fcntl.flock (unchanged). win32: msvcrt.locking of byte 0; a locking OSError
    (LK_LOCK gives up after ~10s) means proceed unlocked. Neither module: no lock (best effort)."""
    if fcntl is not None:
        fcntl.flock(fh, fcntl.LOCK_EX)
    elif msvcrt is not None:
        try:
            fh.seek(0)  # ponytail: locks 1 byte at offset 0 (works on the empty lock file too)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        except OSError:
            pass


def _unlock(fh):
    if fcntl is not None:
        fcntl.flock(fh, fcntl.LOCK_UN)
    elif msvcrt is not None:
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


def cap_check(cap, parent, parent_agent, tuid, now, d=None):
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
        _lock(lock)
        try:
            rows = []
            for lp in cap_logs(d):
                rows += read_log_rows(lp)
            anc = Ancestry(rows)
            kind, root = anc.root_key({"parent_spawn_id": parent, "parent_agent": parent_agent}, include_root)
            if kind == "none":
                return "exempt", False, 0, None
            if kind == "unresolved":
                return "unresolved", False, 0, root
            running, start_tuids = count_running(rows, root, types, stale, now, anc, include_root)
            fresh = []
            try:
                with open(slots, encoding="utf-8") as f:
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
            with open(slots, "w", encoding="utf-8") as f:
                for r in keep:
                    f.write(json.dumps(r) + "\n")
            return "ok", denied, total, root
        finally:
            _unlock(lock)


def cap_message(n, max_n, root):
    pd = root[3:] if (root or "").startswith("pd:") else (root or "?")
    return ("[spawn-cap] %d Execs already running under PD %s tree (cap %d, Exec cap policy: max %d Execs per PD "
            "across all its coords). Please wait for a slot - a completion notification arrives on its own - "
            "then spawn again, or merge tasks. Do not retry in a loop." % (n, pd, max_n, max_n))


# ---- main -----------------------------------------------------------------

def result(action="pass", model=None, old=None, new=None, reason="", deny=None, effort=None, effort_category=None):
    out = {"action": action, "model": model, "old": old, "new": new, "reason": reason}
    if deny is not None:
        out["deny"] = deny
    else:  # a deny carries no effort keys; every other result does (null = no effort decided)
        out["effort"] = effort
        out["effort_category"] = effort_category
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
        effort_step(d, None, d.get("tool_use_id") or "", d.get("parent_spawn_id") or "", d.get("subagent_type") or "")
        return result(model=param, old=param, reason="untouched: fork/teammate/workflow")
    if spawn_project is None and SPAWN_PROJECT_ERROR:  # shared module missing: global log only, say so (fail open)
        append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": d.get("tool_use_id", ""),
                    "subagent_type": d.get("subagent_type", ""),
                    "error": "spawn_project import: %s (global log only)" % SPAWN_PROJECT_ERROR}, d)
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
            status, denied, total, root = cap_check(cap, parent, parent_agent, tuid, now_epoch(), d)
        except Exception as e:  # the cap fails open on its own; the rewrite below still applies
            denied, total = False, 0
            append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "error": "cap: %s: %s" % (type(e).__name__, e)}, d)
        if status == "unresolved":  # exactly one best-effort row per call; pass, never a per-parent count
            append_row({"event": "model_pin_error", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "parent_spawn_id": parent,
                        "error": "cap: ancestry unresolved (no spawn_start row for %s); no PD root found, "
                                 "cap skipped (fail open)" % root}, d)
        if denied:
            max_n = int(cap.get("max", 5))
            append_row({"event": "spawn_denied", "ts": iso(now_epoch()), "tool_use_id": tuid,
                        "subagent_type": subagent_type, "parent_spawn_id": parent, "root": root,
                        "running": total, "cap": max_n, "reason": "spawn_cap"}, d)
            return result("deny", None, param, None, "spawn_cap", cap_message(total, max_n, root))

    if action == "rewrite":
        append_row({"event": "model_override", "ts": iso(now_epoch()), "tool_use_id": tuid,
                    "subagent_type": subagent_type, "old": old, "new": new, "reason": reason,
                    "parent_spawn_id": parent}, d)
    out["effort"], out["effort_category"] = effort_step(d, m, tuid, parent, subagent_type)
    return out


def _utf8_stdio():
    """The Node side sends UTF-8 JSON; on Windows the std streams default to the locale code page. Never raises."""
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors=s.errors)  # keep each stream's error policy
        except Exception:
            pass


def main():
    _utf8_stdio()
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
                    "subagent_type": ctx.get("subagent_type", ""), "error": "%s: %s" % (type(e).__name__, e)}, ctx)
    try:
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
