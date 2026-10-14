#!/usr/bin/env python3
"""jev_spawn.py - shared core for binding Jev skill routing on spawns (verdict line, exempt list,
decision table, route cache). Stdlib only; Python 3.9+ (macOS /usr/bin/python3 included). Importing has NO
side effects (no file reads, no env reads, no dirs). Part of the opt-in skill router: nothing here runs unless
skill-route.py is enabled (AGENCY_SKILL_ROUTER=1); see scripts/skill-route/README.md.

Public API (pinned; downstream: skill-route.py and the spawn recorder; also the jev gate, when you enable one)
-----------
    VERDICTS = ("accept","modify","reject","unavailable");  LINE_RE (re.I|re.M);  REASON_CAP = 200
    EXEMPT_TYPES / EXEMPT_PREFIXES / EXEMPT_SUFFIXES         # one commented block; empty it to make all binding
    is_binding(subagent_type, fork=False) -> bool
    parse_verdict_line(text) -> None | {"id","verdict","reason","line"}   # first match wins
    strip_verdict_line(text) -> str                                       # drops EVERY Jev line
    format_line(route_id, verdict, reason) -> "Jev[r=<id>]: <verdict> — <reason>"
    normalise_verdict(spawner_skills, jev_skills) -> accept|modify|reject
    is_outage(jev) -> bool
    evaluate(jev, spawner_skills, line, route_id="", denies=0, outage=None) -> dict
        keys exactly: decision (pass|rewrite|deny), spawn_verdict, verdict_source, reason,
        inject_skills (list), inject_line (str|None), deny_message (str|None)
        inject_line semantics: non-None = "put this Jev line in the prompt". When the prompt already has a
        Jev line it REPLACES it; when it has none it is APPENDED. apply_decision() does exactly that.
    apply_decision(prompt, decision) -> new prompt   # replace/append Jev line; prepend `Skills: /a, /b` when
                                                     # inject_skills AND the prompt has no Skills line yet
    build_deny_message(route_id, jev, spawner_skills, rule, role="exec") -> str
    cache_dir(); cache_put(res, meta=None) -> route_id ("" on failure); cache_get(route_id) -> dict|None;
    cache_bump_denies(route_id) -> int (0 on failure); CACHE_TTL_SECONDS = 48h; CACHE_PRUNE_THRESHOLD = 500
    Cache functions NEVER raise. Entries hold NO task text.
    spawner_key(spawner, routing_text) -> 16 hex = sha256(spawner or "root" + "\\0" + routing_text)[:16]
    spawner_dir(); spawner_denies(key) -> int (0 on missing/expired/corrupt/failure);
    spawner_bump_denies(key) -> int (0 on failure); SPAWNER_TTL_SECONDS = 1h
        SECOND loop guard, per spawner + task: $SKILL_ROUTE_STATE_DIR/jev-gate-denies/<key>.json. A spawner that
        re-issues WITHOUT the Jev line gets a fresh route id each time, so the per-route-id denies never reach the
        cap; the gate uses max(route-id denies, spawner denies) and bumps both. routing_text is the text the gate
        routes on (Skills clause, slash tokens and Jev line stripped). Never raises; entries hold NO task text.

jev dict (cache-entry shaped; missing keys tolerated): skills, gate, router, none_fired, confidential, jev_down.
`confidential` is for a content filter you add yourself (one that keeps a task off every model); the router shipped
here has none, so skill-route.py never sets it and it is always false.
Effective gate: "pass" only when gate == "pass" AND not none_fired AND not confidential; anything else
(including a missing gate) is low_confidence. Evaluation order: outage rows ->
reason checks (low_confidence needs a reason for ANY verdict; modify/reject always need one) -> accept rows
(empty Skills -> inject Jev's; differing Skills -> deny) -> otherwise-valid pass. So `Jev: accept` with no reason
on a low_confidence gate is denied even when Skills are empty.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time

try:  # POSIX lock for the deny counter; absent -> best-effort atomic replace only
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

VERDICTS = ("accept", "modify", "reject", "unavailable")
LINE_RE = re.compile(
    r"^[ \t>*-]*Jev(?:\[r=(?P<id>[0-9a-f]{8})\])?[ \t]*:[ \t]*(?P<verdict>accept|modify|reject|unavailable)\b"
    r"[ \t]*(?:[—–:-]+[ \t]*)?(?P<reason>.*)$",
    re.I | re.M,
)
REASON_CAP = 200
_SKILLS_LINE_RE = re.compile(r"(?im)^[ \t>*-]*skills?(?:[ \t]+to[ \t]+(?:load|use))?[ \t]*:[ \t]*(.*)$")

# --- EXEMPT SPAWN TYPES: no enforcement, no feedback record. Everything NOT listed here is binding. ---
# Set all three constants to () to make every spawn binding. Matching is case-insensitive.
EXEMPT_TYPES = (
    "codebase-search", "save-state-runner", "project-scaffolder", "Delegator", "Explore", "Plan",
    "statusline-setup", "claude-code-guide", "architecture-analyzer", "article-analyzer", "assemble-reviewer",
    "domain-analyzer", "file-analyzer", "graph-reviewer", "knowledge-graph-guide", "project-scanner",
    "tour-builder",
)
EXEMPT_PREFIXES = ("critique-", "council-", "caveman:")
EXEMPT_SUFFIXES = ("-critique",)
# --- end exempt block ---


def is_binding(subagent_type, fork=False):
    if fork:
        return False
    t = (subagent_type or "").strip().lower()
    if not t:
        return True
    if t in {x.lower() for x in EXEMPT_TYPES}:
        return False
    if any(t.startswith(p.lower()) for p in EXEMPT_PREFIXES):
        return False
    if any(t.endswith(s.lower()) for s in EXEMPT_SUFFIXES):
        return False
    return True


# ---------------------------------------------------------------- verdict line

def _result(m):
    return {"id": (m.group("id").lower() if m.group("id") else None),
            "verdict": m.group("verdict").lower(),
            "reason": m.group("reason").strip()[:REASON_CAP],
            "line": m.group(0).strip()}


def parse_verdict_line(text):
    m = LINE_RE.search(text or "")
    return _result(m) if m else None


def strip_verdict_line(text):
    if not text:
        return text or ""
    return "\n".join(p for p in text.split("\n") if not LINE_RE.match(p))


def format_line(route_id, verdict, reason):
    tag = "[r=%s]" % route_id if route_id else ""
    tail = " — %s" % reason if reason else ""
    return "Jev%s: %s%s" % (tag, verdict, tail)


# ---------------------------------------------------------------- decision

def _set(skills):
    return {str(s).strip().lstrip("/").lower() for s in (skills or []) if str(s).strip().lstrip("/")}


def normalise_verdict(spawner_skills, jev_skills):
    s, j = _set(spawner_skills), _set(jev_skills)
    if not s and not j:
        return "accept"
    if not s:
        return "reject"
    if s == j:
        return "accept"
    return "modify" if s & j else "reject"


def is_outage(jev):
    jev = jev or {}
    return jev.get("router") not in ("jev", "passthrough") and not jev.get("confidential")


def _slash(skills):
    return ", ".join("/" + str(s).lstrip("/") for s in skills) or "(none)"


def build_deny_message(route_id, jev, spawner_skills, rule, role="exec"):
    jev = jev or {}
    rid = route_id or ""
    return "\n".join([
        "JEV_SPAWN_DENY route=%s rule=%s" % (rid or "(none)", rule),
        "gate=%s router=%s none_fired=%s confidential=%s" % (
            jev.get("gate"), jev.get("router"), bool(jev.get("none_fired")), bool(jev.get("confidential"))),
        "jev_skills: %s" % _slash(jev.get("skills") or []),
        "spawner_skills: %s" % _slash(spawner_skills or []),
        "Add ONE of these lines to the prompt (accept = Skills equal Jev; modify = overlap; reject = disjoint;"
        " reason required for modify/reject and whenever gate is low_confidence):",
        format_line(rid, "accept", "<reason>"),
        format_line(rid, "modify", "<reason>"),
        format_line(rid, "reject", "<reason>"),
        'Pre-consult next time (skips this round-trip): python3 %s --role %s "<task>"' % (
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill-route.py"), role),
        "Re-issue the same Agent call with the line added.",
    ])


def _out(decision, spawn_verdict=None, verdict_source=None, reason="", inject_skills=None, inject_line=None,
         deny_message=None):
    return {"decision": decision, "spawn_verdict": spawn_verdict, "verdict_source": verdict_source,
            "reason": reason, "inject_skills": list(inject_skills or []), "inject_line": inject_line,
            "deny_message": deny_message}


def evaluate(jev, spawner_skills, line, route_id="", denies=0, outage=None):
    jev = jev or {}
    J = list(jev.get("skills") or [])
    S = list(spawner_skills or [])
    gate_pass = (jev.get("gate") == "pass") and not jev.get("none_fired") and not jev.get("confidential")
    if outage is None:
        outage = is_outage(jev)
    norm = normalise_verdict(S, J)
    same = _set(S) == _set(J)
    rid = route_id or ""

    def deny(rule):
        if denies >= 2:  # loop guard: the spawner already got two denies for this route id
            return _out("pass", norm, "deny_cap", "deny_cap after %d denies (%s)" % (denies, rule))
        return _out("deny", reason=rule, deny_message=build_deny_message(rid, jev, S, rule))

    def add_id():  # [r=id] missing on an otherwise valid line -> replace it with the id-carrying line
        if line and not line.get("id") and rid:
            return format_line(rid, line["verdict"], line["reason"])
        return None

    if outage:
        if line:
            return _out("pass", norm, "explicit", line["reason"])
        r = "router=%s" % jev.get("router")
        return _out("rewrite", "unreviewed", "jev_unavailable", r,
                    inject_line=format_line(rid, "unavailable", r))
    if line:
        v = line["verdict"]
        if not gate_pass and not line["reason"]:
            return deny("reason required on low_confidence")
        if v in ("modify", "reject") and not line["reason"]:
            return deny("reason required for modify/reject")
        if v == "accept" and not S and J:
            return _out("rewrite", "accept", "explicit", line["reason"], inject_skills=J, inject_line=add_id())
        if v == "accept" and S and not same:
            return deny("accept but Skills differ: use modify")
        inj = add_id()
        return _out("rewrite" if inj else "pass", norm, "explicit", line["reason"], inject_line=inj)
    if gate_pass:
        if J and not S:
            r = "auto: Jev default (gate pass)"
            return _out("rewrite", "accept", "auto_default", r, inject_skills=J,
                        inject_line=format_line(rid, "accept", r))
        if same:
            r = "auto: matches Jev (gate pass)"
            return _out("rewrite", "accept", "auto_match", r, inject_line=format_line(rid, "accept", r))
        return deny("no Jev line and Skills differ from Jev")
    return deny("no Jev line and gate is low_confidence")


def apply_decision(prompt, decision):
    p = prompt or ""
    d = decision or {}
    line = d.get("inject_line")
    if line:
        m = LINE_RE.search(p)
        if m:
            p = p[:m.start()] + line + p[m.end():]
        else:
            if p and not p.endswith("\n"):
                p += "\n"
            p += line
    skills = d.get("inject_skills") or []
    if skills and not _SKILLS_LINE_RE.search(p):
        p = "Skills: %s\n%s" % (_slash(skills), p)
    return p


# ---------------------------------------------------------------- route cache

CACHE_TTL_SECONDS = 48 * 3600
CACHE_PRUNE_THRESHOLD = 500
_ID_RE = re.compile(r"[0-9a-f]{8}")
_KEYS = ("route_id", "ts", "skills", "gate", "router", "domain", "role", "none_fired", "confidential",
         "jev_down", "denies")


# Python twin of hooks/lib/resolve-root.sh: same precedence, same default,
# byte-identical to the copy carried by every hook and script (enforced by
# .github/scripts/check-hardcoded-root.sh).
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


def _state_base():
    """Same state dir skill-route.py uses: $SKILL_ROUTE_STATE_DIR, else {root}/state/skill-route."""
    return os.environ.get("SKILL_ROUTE_STATE_DIR") or os.path.join(
        agency_root(os.path.expanduser("~")), "state", "skill-route")


def cache_dir():
    return os.path.join(_state_base(), "jev-route-cache")


def _valid_id(route_id):
    return isinstance(route_id, str) and _ID_RE.fullmatch(route_id) is not None


def _write_atomic(path, entry):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _expired(entry, path, now, ttl=None):
    try:
        ts = float(entry.get("ts"))
    except (TypeError, ValueError):
        ts = now
    try:
        mt = os.path.getmtime(path)
    except OSError:
        mt = now
    return (now - min(ts, mt)) > (CACHE_TTL_SECONDS if ttl is None else ttl)


def _prune(d, now, ttl=None):
    ttl = CACHE_TTL_SECONDS if ttl is None else ttl
    files = []
    for name in os.listdir(d):
        if name.endswith(".json"):
            p = os.path.join(d, name)
            try:
                files.append((os.path.getmtime(p), p))
            except OSError:
                pass
    if len(files) <= CACHE_PRUNE_THRESHOLD:
        return
    keep = []
    for mt, p in files:
        if now - mt > ttl:
            try:
                os.unlink(p)
            except OSError:
                pass
        else:
            keep.append((mt, p))
    keep.sort()
    for mt, p in keep[:max(0, len(keep) - CACHE_PRUNE_THRESHOLD)]:
        try:
            os.unlink(p)
        except OSError:
            pass


def cache_put(res, meta=None):
    try:
        res, meta = res or {}, meta or {}
        now = time.time()
        d = cache_dir()
        os.makedirs(d, exist_ok=True)
        skills = [str(s) for s in (res.get("skills") or [])]
        basis = json.dumps([skills, res.get("router")], sort_keys=True)  # never task text
        for _ in range(5):
            rid = hashlib.sha256((basis + repr(now) + os.urandom(8).hex()).encode("utf-8")).hexdigest()[:8]
            path = os.path.join(d, rid + ".json")
            if not os.path.exists(path):
                break
        entry = {"route_id": rid, "ts": now, "skills": skills, "gate": res.get("gate"),
                 "router": res.get("router"), "domain": res.get("domain"), "role": meta.get("role"),
                 "none_fired": bool(meta.get("none_fired")), "confidential": bool(meta.get("confidential")),
                 "jev_down": bool(res.get("jev_down", meta.get("jev_down", False))), "denies": 0}
        _write_atomic(path, entry)
        try:
            _prune(d, now)
        except Exception:
            pass
        return rid
    except Exception:
        return ""


def cache_get(route_id):
    try:
        if not _valid_id(route_id):
            return None
        path = os.path.join(cache_dir(), route_id + ".json")
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        if not isinstance(entry, dict) or _expired(entry, path, time.time()):
            return None
        return entry
    except Exception:
        return None


def cache_bump_denies(route_id):
    lock = None
    try:
        if not _valid_id(route_id):
            return 0
        d = cache_dir()
        path = os.path.join(d, route_id + ".json")
        if not os.path.exists(path):
            return 0
        if fcntl is not None:
            lock = open(os.path.join(d, ".lock"), "a")
            fcntl.flock(lock, fcntl.LOCK_EX)
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        if not isinstance(entry, dict):
            return 0
        entry["denies"] = int(entry.get("denies") or 0) + 1
        _write_atomic(path, entry)
        return entry["denies"]
    except Exception:
        return 0
    finally:
        if lock is not None:
            try:
                lock.close()  # releases the flock
            except Exception:
                pass


# ---------------------------------------------------------------- spawner loop guard (second deny guard)

SPAWNER_TTL_SECONDS = 3600
_KEY_RE = re.compile(r"[0-9a-f]{16}")


def spawner_key(spawner, routing_text):
    """16 hex = sha256((spawner or "root") + NUL + routing_text)[:16]. Never raises."""
    try:
        sp = spawner if isinstance(spawner, str) and spawner else "root"
        txt = routing_text if isinstance(routing_text, str) else ""
        return hashlib.sha256((sp + "\0" + txt).encode("utf-8", "replace")).hexdigest()[:16]
    except Exception:
        return ""


def spawner_dir():
    return os.path.join(_state_base(), "jev-gate-denies")


def _valid_key(key):
    return isinstance(key, str) and _KEY_RE.fullmatch(key) is not None


def _spawner_read(path, now):
    """Live denies count of one spawner entry; 0 when missing, expired (> 1h), corrupt or malformed."""
    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        if not isinstance(entry, dict) or _expired(entry, path, now, SPAWNER_TTL_SECONDS):
            return 0
        return max(0, int(entry.get("denies") or 0))
    except Exception:
        return 0


def spawner_denies(key):
    try:
        if not _valid_key(key):
            return 0
        return _spawner_read(os.path.join(spawner_dir(), key + ".json"), time.time())
    except Exception:
        return 0


def spawner_bump_denies(key):
    lock = None
    try:
        if not _valid_key(key):
            return 0
        now = time.time()
        d = spawner_dir()
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, key + ".json")
        if fcntl is not None:
            lock = open(os.path.join(d, ".lock"), "a")
            fcntl.flock(lock, fcntl.LOCK_EX)
        n = _spawner_read(path, now) + 1
        _write_atomic(path, {"key": key, "ts": now, "denies": n})
        try:
            _prune(d, now, SPAWNER_TTL_SECONDS)
        except Exception:
            pass
        return n
    except Exception:
        return 0
    finally:
        if lock is not None:
            try:
                lock.close()
            except Exception:
                pass
