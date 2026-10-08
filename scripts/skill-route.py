#!/usr/bin/env python3
"""skill-route.py - Jev skill router: pick 0-3 skills for a task text, plus a model tier and a tool profile.

OFF BY DEFAULT. The router runs only when the environment variable AGENCY_SKILL_ROUTER is exactly "1".
With anything else (unset, "0", "true", ...) EVERY command-line invocation - any arguments, --shadow,
--rebuild-menu, stdin - prints exactly one JSON line and exits 0, before any network, subprocess or file
write, and before jev_client is even imported:
    {"router":"disabled","enabled":false,"skills":[],"reason":"AGENCY_SKILL_ROUTER is not 1",
     "fallback":"pick 1-3 skills from skills/INDEX.md","enable":"see scripts/skill-route/README.md"}
Enable steps (your own TypeSafe key, the switch, menu rebuild, verification): scripts/skill-route/README.md.

0 skills = "no listed skill fits" (gate low_confidence). Stdlib only; runs on Python 3.9+ (macOS
/usr/bin/python3 included). Importing has NO side effects: the module top level imports only the standard
library, and jev_client is imported lazily, only on the routing path.

Module API (other tools load this file in-process via importlib spec_from_file_location)
    class MenuError(Exception)
    router_enabled() -> bool                     # AGENCY_SKILL_ROUTER == "1"
    load_menu(rebuild=False, strict=True) -> {"skills": {name: {"description","triggers","domain","also","hint"}},
                                 "domains": {name: desc}, "excluded": {name: reason}, "unassigned": [name, ...],
                                 "vi_map": {...}, "en_only": [...], "built_at": iso}
    menu_stats(menu) -> {"routable","excluded","excluded_names","domains"}
    route(text, project=None, router=None, mode=None, log=True, cwd=None) -> contract dict
    main(argv=None) -> exit code
load_menu() and menu_stats() work offline whether or not the switch is on (the CI menu gate uses them).
strict (default, for importers: the CI gate, jev-gate-check.py --only menu-build): a skill dir with no overlay
entry raises MenuError. lenient (strict=False, what route() and the CLI use): such a skill is excluded with reason
"unassigned" and listed in menu["unassigned"]; main() prints ONE stderr warning. Every other overlay problem raises.
route() called in-process with the switch off never reaches a model: jev_client.ask() raises
RouterUnavailable("disabled") and route() degrades to the grep router.

route() returns exactly {"skills","model","tools","scores","domain","router","gate","pre_rules","lang",
"jev_down"}. It never prints and never raises EXCEPT MenuError (a broken menu/overlay is a config bug that
must fail loud; with no menu there is nothing to fall back to). Every network/Jev/Haiku failure degrades
to the grep router. pre_rules: "explicit" (/name passthrough), "vietnamese".

Root: {root} = $AGENCY_HOME, else $CLAUDE_CONFIG_DIR, else <home>/.claude (hooks/lib/resolve-root.sh).

Environment (all optional; tests set them)
    AGENCY_SKILL_ROUTER      "1" enables the router; anything else = disabled
    SKILL_ROUTE_SKILLS_DIR   skills dir (default {root}/skills); INDEX.catalog.json is read from it if present
    SKILL_ROUTE_OVERLAY      overlay json (default <scripts>/skill-route/overlay.json)
    SKILL_ROUTE_STATE_DIR    state dir (default {root}/state/skill-route): menu cache, jev-down flag,
                             shadow kill switch (skill-route-shadow.off)
    SKILL_ROUTE_LOG          decision log (default {root}/memory/metrics/skill-route.jsonl)
    SKILL_ROUTE_SHADOW_LOG   shadow log (default {root}/memory/metrics/skill-route-shadow.jsonl)
    SKILL_ROUTE_CHILD=1      make --shadow a no-op (recursion guard; set by the Haiku child)
    JEV_* / jev_client env   see jev_client.py (JEV_ENV_FILE, JEV_PURPOSE, JEV_USAGE_LOG, JEV_ENDPOINT, ...)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import shlex
import sys
import unicodedata
import warnings

# --------------------------------------------------------------------------- opt-in switch
SWITCH_ENV = "AGENCY_SKILL_ROUTER"
# Printed verbatim (one line) by every CLI invocation while the switch is off. Do not reformat: callers and
# the CI no-network test compare it byte for byte.
DISABLED_LINE = ('{"router":"disabled","enabled":false,"skills":[],"reason":"AGENCY_SKILL_ROUTER is not 1",'
                 '"fallback":"pick 1-3 skills from skills/INDEX.md","enable":"see scripts/skill-route/README.md"}')


def router_enabled():
    """True only when AGENCY_SKILL_ROUTER is exactly "1". Same rule as jev_client.router_enabled()."""
    return os.environ.get(SWITCH_ENV) == "1"


_JEV = None


def _jev():
    """jev_client, imported on first use (routing path only). Never called while the CLI is disabled."""
    global _JEV
    if _JEV is None:
        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.insert(0, d)
        import jev_client
        _JEV = jev_client
    return _JEV


# --------------------------------------------------------------------------- constants (tune on DEV only)
T1 = 0.45                 # flat gate: top1 merged prob must be >= T1
T2 = 0.10                 # flat gate: top1 - top2 must be >= T2
TS_T1 = 0.50              # two-stage gate: combined p = domain_p * skill_p must be >= TS_T1
TS_T2 = 0.10              # two-stage gate: domain_p * (skill_p1 - skill_p2) must be >= TS_T2
#   (TS_*: dev sweep, clean dev n=94: every TS_T1 <= 0.50 / TS_T2 <= 0.10 ties at pass 96.8%,
#    acc|pass 98.9%; the strictest point of that plateau was taken. See skill-route/README.md "Gate".)
NONE_T = 0.40             # `none` fires when it wins its question(s) OR holds >= NONE_T
#   (highest p(none) on a correct dev pick was 0.29; dev has no true-none cases to tune on)
RANK_MIN_PROB = 0.15      # ranks 2-3 are returned only when prob >= this
MAX_SKILLS = 3
DEFAULT_MODE = "two-stage"   # eval decides the long-term default (report both numbers)
DEFAULT_ROUTER = "jev"
PURPOSE = "skill-route"
CHOICE_MAX_OPTIONS = 255     # Jev Choice limit
CHUNK_SKILLS = CHOICE_MAX_OPTIONS - 1   # skills per skill question (+1 slot for `none`, always offered)
NONE_KEY = "none"
NONE_TEXT = ("No listed skill fits this task: it needs no special skill, or a skill that is not in this list. "
             "Pick only when every listed skill would be a stretch.")
SHADOW_TEXT_CAP = 3000
EXCERPT_CAP = 200
MAX_QUESTION_CHARS = 90000   # per-question criteria budget (~25k tokens; Jev: state + longest question ~32k)
MAX_TOTAL_CHARS = 150000     # all questions together (~42k tokens; Jev: all ~64k)
TWO_STAGE_DESC_CHARS = 260
TWO_STAGE_HINT_CHARS = 200
FLAT_DESC_CHARS = 140
FLAT_HINT_CHARS = 120
MIN_DESC_CHARS = 60
GREP_DEFAULT_MODEL = "sonnet"
GREP_DEFAULT_TOOLS = "edit"
PASSTHROUGH_MODEL = "sonnet"
PASSTHROUGH_TOOLS = "edit"
MODES = ("two-stage", "flat")
ROUTERS = ("jev", "haiku", "grep")
MODEL_TIERS = ("haiku", "sonnet", "opus")
TOOL_PROFILES = ("read-only", "edit", "web", "full")

MODEL_CRITERIA = {
    "haiku": "Trivial or mechanical task: tiny edit, formatting, rename, simple lookup, file move, short summary.",
    "sonnet": "Normal implementation, writing, analysis or research task with a clear spec and bounded scope.",
    "opus": "Hard reasoning: architecture, ambiguous multi-step design, deep debugging, high-stakes review or strategy.",
}
TOOLS_CRITERIA = {
    "read-only": "Only reads, searches and analyzes; writes or changes nothing.",
    "edit": "Reads and edits or creates local files and runs local commands; no web needed.",
    "web": "Needs web search, web fetch or a browser in addition to local file work.",
    "full": "Needs broad access: deploys, external services or APIs, MCP tools, accounts, or many systems at once.",
}

_VI_CHARS = (
    "ăâđêôơư" "ảãạẻẽẹỉĩịỏõọủũụỳýỷỹỵ"
    "ằắẳẵặầấẩẫậềếểễệồốổỗộờớởỡợừứửữự"
)
# acute/grave on plain a/e/i/o/u are shared with French/Spanish, so they do not count toward the threshold
_VI_SET = set(_VI_CHARS + _VI_CHARS.upper())
_VI_WORD_RE = re.compile(r"tiếng\s+việt|vietnamese|\bVN\b", re.I)


UNASSIGNED = "unassigned"  # menu["excluded"] reason of a skill dir with no overlay entry (lenient mode)


class MenuError(Exception):
    """The skill menu cannot be built (unassigned skills / unknown domains). Message lists every problem."""


# --------------------------------------------------------------------------- paths
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


def _home():
    return os.path.expanduser("~")


def _root():
    return agency_root(_home())


def _scripts_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _skills_dir():
    return os.environ.get("SKILL_ROUTE_SKILLS_DIR") or os.path.join(_root(), "skills")


def _overlay_path():
    return os.environ.get("SKILL_ROUTE_OVERLAY") or os.path.join(_scripts_dir(), "skill-route", "overlay.json")


def _state_dir():
    return os.environ.get("SKILL_ROUTE_STATE_DIR") or os.path.join(_root(), "state", "skill-route")


def _metrics_dir():
    return os.path.join(_root(), "memory", "metrics")


def _menu_cache_path():
    return os.path.join(_state_dir(), "skill-route-menu.json")


def _decision_log_path():
    return os.environ.get("SKILL_ROUTE_LOG") or os.path.join(_metrics_dir(), "skill-route.jsonl")


def _shadow_log_path():
    return os.environ.get("SKILL_ROUTE_SHADOW_LOG") or os.path.join(_metrics_dir(), "skill-route-shadow.jsonl")


def _shadow_off_path():
    return os.path.join(_state_dir(), "skill-route-shadow.off")


def _usage_log_path():
    return os.environ.get("JEV_USAGE_LOG") or os.path.join(_metrics_dir(), "jev-usage.jsonl")


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_jsonl(path, rec):
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except Exception:
        pass


# --------------------------------------------------------------------------- frontmatter (stdlib, no yaml)
def _dq_end(s):
    """Index of the closing double quote of a YAML dq scalar starting at s[0] == '"', or -1."""
    i = 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            return i
        i += 1
    return -1


def _sq_end(s):
    i = 1
    while i < len(s):
        if s[i] == "'":
            if i + 1 < len(s) and s[i + 1] == "'":
                i += 2
                continue
            return i
        i += 1
    return -1


def _unquote_dq(s):
    end = _dq_end(s)
    body = s if end < 0 else s[:end + 1]
    try:
        return json.loads(body)
    except ValueError:
        return body.strip('"').replace('\\"', '"').replace("\\\\", "\\")


def _unquote_sq(s):
    end = _sq_end(s)
    body = s[1:] if end < 0 else s[1:end]
    return body.replace("''", "'")


def parse_frontmatter(text):
    """Top-level scalar keys of a SKILL.md frontmatter as {key: str}. Handles plain, "dq", 'sq',
    multi-line, and |/> block scalars (whitespace collapsed). Nested mappings are skipped."""
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end = i
            break
    if end is None:
        return {}
    fm = lines[1:end]
    out = {}
    i = 0
    while i < len(fm):
        m = re.match(r"^([A-Za-z_][\w.-]*):[ \t]*(.*)$", fm[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).rstrip()
        i += 1
        if val[:1] in ("|", ">"):
            parts = []
            while i < len(fm) and (fm[i].startswith((" ", "\t")) or not fm[i].strip()):
                parts.append(fm[i].strip())
                i += 1
            out[key] = " ".join(p for p in parts if p)
        elif val[:1] == '"':
            buf = val
            while _dq_end(buf) < 0 and i < len(fm):
                buf += " " + fm[i].strip()
                i += 1
            out[key] = _unquote_dq(buf)
        elif val[:1] == "'":
            buf = val
            while _sq_end(buf) < 0 and i < len(fm):
                buf += " " + fm[i].strip()
                i += 1
            out[key] = _unquote_sq(buf)
        else:
            parts = [val]
            while i < len(fm) and fm[i].startswith((" ", "\t")):
                parts.append(fm[i].strip())
                i += 1
            out[key] = " ".join(p for p in parts if p)
        if isinstance(out.get(key), str):
            out[key] = re.sub(r"\s+", " ", out[key]).strip()
    return out


# --------------------------------------------------------------------------- menu
def _read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _universe(skills_dir):
    """[(name, SKILL.md path)] for depth-1 dirs not starting with '_' (nested dirs are out of scope)."""
    out = []
    try:
        names = sorted(os.listdir(skills_dir))
    except OSError:
        return out
    for n in names:
        if n.startswith("_") or n.startswith("."):
            continue
        p = os.path.join(skills_dir, n, "SKILL.md")
        if os.path.isfile(p):
            out.append((n, p))
    return out


def _source_signature(skills_dir, overlay_path, universe):
    h = hashlib.sha1()
    h.update(("%s\n%s\n" % (os.path.abspath(skills_dir), os.path.abspath(overlay_path))).encode("utf-8"))
    for n, _p in universe:
        h.update((n + "\n").encode("utf-8"))
    return h.hexdigest()


def _newest_source_mtime(universe, overlay_path, catalog_path):
    newest = 0.0
    paths = [p for _n, p in universe] + [overlay_path, catalog_path]
    for p in paths:
        try:
            newest = max(newest, os.stat(p).st_mtime)
        except OSError:
            pass
    return newest


def _build_menu(skills_dir, overlay_path, universe, strict=True):
    try:
        overlay = _read_json(overlay_path)
    except (OSError, ValueError) as e:
        raise MenuError("cannot read overlay %s: %s" % (overlay_path, e.__class__.__name__))
    if not isinstance(overlay, dict):
        raise MenuError("overlay %s is not a JSON object" % overlay_path)
    domains = overlay.get("domains") or {}
    o_skills = overlay.get("skills") or {}
    synthetic = overlay.get("synthetic") or {}

    catalog = {}
    cat_path = os.path.join(skills_dir, "INDEX.catalog.json")
    try:
        for ent in _read_json(cat_path).get("skills", []):
            if isinstance(ent, dict) and ent.get("name"):
                catalog[ent["name"]] = ent
    except (OSError, ValueError, AttributeError):
        pass

    problems = []
    skills = {}
    excluded = {}
    unassigned = []
    for name, path in universe:
        ov = o_skills.get(name)
        if name not in o_skills:
            if strict:
                problems.append("no overlay entry: %s" % name)
            else:
                excluded[name] = UNASSIGNED
                unassigned.append(name)
            continue
        if not isinstance(ov, dict):  # present but malformed: a broken overlay, fatal in both modes
            problems.append("overlay entry is not an object: %s" % name)
            continue
        if ov.get("exclude"):
            excluded[name] = str(ov["exclude"])
            continue
        dom = ov.get("domain")
        if not dom:
            problems.append("no domain: %s" % name)
            continue
        if dom not in domains:
            problems.append("unknown domain %r: %s" % (dom, name))
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                fm = parse_frontmatter(fh.read())
        except OSError:
            fm = {}
        cat = catalog.get(name) or {}
        desc = fm.get("description") or cat.get("description") or name
        trig = cat.get("triggers") if isinstance(cat.get("triggers"), list) else []
        also = [d for d in (ov.get("also_domains") or []) if d != dom]
        bad_also = [d for d in also if d not in domains]
        if bad_also:
            problems.append("unknown also_domains %r: %s" % (bad_also, name))
            continue
        skills[name] = {
            "description": desc,
            "triggers": [str(t) for t in trig],
            "domain": dom,
            "also": also,   # extra domains whose stage-2 question also offers this skill (two-stage only)
            "hint": ov.get("hint") or "",
        }
    on_disk = set(n for n, _p in universe)
    for name, sv in synthetic.items():
        if name in on_disk:
            continue  # a real SKILL.md wins over the synthetic entry
        if not isinstance(sv, dict) or not sv.get("domain"):
            problems.append("synthetic entry without domain: %s" % name)
            continue
        if sv["domain"] not in domains:
            problems.append("unknown domain %r: synthetic %s" % (sv["domain"], name))
            continue
        s_also = [d for d in (sv.get("also_domains") or []) if d != sv["domain"]]
        bad_also = [d for d in s_also if d not in domains]
        if bad_also:
            problems.append("unknown also_domains %r: synthetic %s" % (bad_also, name))
            continue
        skills[name] = {
            "description": sv.get("description") or name,
            "triggers": [str(t) for t in (sv.get("triggers") or [])],
            "domain": sv["domain"],
            "also": s_also,
            "hint": sv.get("hint") or "",
        }
    if problems:
        raise MenuError("skill menu cannot be built (%d problem(s)):\n  %s\nFix: add each skill to %s "
                        "with a valid domain or an exclude reason." % (
                            len(problems), "\n  ".join(problems), overlay_path))
    if not skills:
        raise MenuError("skill menu is empty (skills dir %s, overlay %s%s)" % (
            skills_dir, overlay_path, "; %d skill(s) have no overlay entry" % len(unassigned) if unassigned else ""))
    return {
        "skills": skills,
        "domains": dict(domains),
        "excluded": excluded,
        "unassigned": sorted(unassigned),
        "vi_map": dict(overlay.get("vi_map") or {}),
        "en_only": list(overlay.get("en_only") or []),
        "built_at": _now_iso(),
    }


def load_menu(rebuild=False, strict=True):
    """Build (or load the cached) skill menu.

    strict=True (default): a skill dir with no overlay entry raises MenuError listing them (CI gate, gate check).
    strict=False (runtime): such skills are excluded as "unassigned" and listed in menu["unassigned"].
    Every other problem raises MenuError in both modes. One cache file serves both modes: a strict caller never
    gets a cached menu that has unassigned skills (it falls through to a rebuild, which raises the strict error).
    """
    skills_dir = _skills_dir()
    overlay_path = _overlay_path()
    cat_path = os.path.join(skills_dir, "INDEX.catalog.json")
    universe = _universe(skills_dir)
    sig = _source_signature(skills_dir, overlay_path, universe)
    cache = _menu_cache_path()
    if not rebuild:
        try:
            cache_mtime = os.stat(cache).st_mtime
            if cache_mtime >= _newest_source_mtime(universe, overlay_path, cat_path):
                data = _read_json(cache)
                if isinstance(data, dict) and data.get("sig") == sig and "skills" in data \
                        and not (strict and data.get("unassigned")):
                    data.setdefault("unassigned", [])
                    return data
        except (OSError, ValueError):
            pass
    menu = _build_menu(skills_dir, overlay_path, universe, strict)  # raises MenuError, cache untouched
    menu["sig"] = sig
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        tmp = "%s.tmp.%d" % (cache, os.getpid())
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(menu, fh, ensure_ascii=False)
        os.replace(tmp, cache)
    except OSError:
        pass
    return menu


def menu_stats(menu):
    per = {}
    for n, s in menu["skills"].items():
        per[s["domain"]] = per.get(s["domain"], 0) + 1
    return {"routable": len(menu["skills"]), "excluded": len(menu["excluded"]),
            "excluded_names": dict(menu["excluded"]), "domains": per}


# --------------------------------------------------------------------------- text helpers
def _squash(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _trim(s, n):
    s = _squash(s)
    if n <= 0:
        return ""
    if len(s) <= n:
        return s
    cut = s[:n]
    sp = cut.rfind(" ")
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(" ,;:.-") + "..."


def _criteria_text(entry, desc_chars, hint_chars):
    text = _trim(entry.get("description", ""), desc_chars)
    hint = _trim(entry.get("hint", ""), hint_chars)
    if hint:
        text = (text + " | Hint: " + hint) if text else "Hint: " + hint
    return text or entry.get("domain", "skill")


def detect_lang(text):
    n = sum(1 for ch in text if ch in _VI_SET)
    if n >= 3 or _VI_WORD_RE.search(text):
        return "vi"
    return "en"


_SLASH_RE = re.compile(r"(?<![\w/.~:-])/([A-Za-z0-9][\w:-]*)(?![/\w]|\.\w)")


def slash_tokens(text, names):
    """Ordered unique menu names referenced as /name in text (case-insensitive; menu names only)."""
    lower = dict((n.lower(), n) for n in names)
    out = []
    for m in _SLASH_RE.finditer(text or ""):
        n = lower.get(m.group(1).lower())
        if n and n not in out:
            out.append(n)
    return out


def strip_slash_tokens(text, names):
    lower = set(n.lower() for n in names)
    return _SLASH_RE.sub(lambda m: "" if m.group(1).lower() in lower else m.group(0), text or "")


# --------------------------------------------------------------------------- grep router
_STOP = set("""the and for with that this from into your you are not but use when what how can will have has been
was were its their them then than they our out all any one two new add make get set run using used just only also
more most some such via per each want need please should would could about over under after before while which
who whom does did done it's""".split())


def _fold(s):
    s = unicodedata.normalize("NFKD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def _stem(t):
    for suf in ("ing", "ers", "er", "es", "ed", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[:-len(suf)]
    return t


def _seq(s):
    return [_stem(t) for t in re.findall(r"[a-z0-9]{3,}", _fold(s)) if t not in _STOP]


def _toks(s):
    return set(_seq(s))


def grep_route(text, menu, names=None):
    """Token-overlap router (idf-weighted: name 3x, trigger 2x, description/hint 1x, +adjacent-pair bonus).
    Returns ranked [(skill, share)] where share = score / sum of the top-5 scores (relative, not calibrated)."""
    skills = menu["skills"]
    names = list(names) if names is not None else list(skills)
    qseq = _seq(text)
    q = set(qseq)
    if not q or not names:
        return []
    qpairs = set(zip(qseq, qseq[1:]))
    docs = {}
    pairs = {}
    df = {}
    for n in names:
        s = skills[n]
        full = " ".join([s.get("description", ""), s.get("hint", ""), " ".join(s.get("triggers") or [])])
        dseq = _seq(full)
        pairs[n] = set(zip(dseq, dseq[1:]))
        w = {}
        for t in _toks(s.get("description", "") + " " + s.get("hint", "")):
            w[t] = 1.0
        for t in _toks(" ".join(s.get("triggers") or [])):
            w[t] = max(w.get(t, 0), 2.0)
        for t in _toks(n.replace("-", " ")):
            w[t] = max(w.get(t, 0), 3.0)
        docs[n] = w
        for t in w:
            df[t] = df.get(t, 0) + 1
    big_n = float(len(names))
    scores = {}
    for n, w in docs.items():
        sc = 0.0
        for t in q:
            if t in w:
                sc += math.log(1.0 + big_n / df[t]) * w[t]
        for a, b in qpairs & pairs[n]:  # phrase bonus: two query words adjacent in the skill text
            sc += 1.5 * 0.5 * (math.log(1.0 + big_n / df[a]) + math.log(1.0 + big_n / df[b]))
        if sc > 0:
            scores[n] = sc
    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    total = sum(sc for _n, sc in ranked[:5])  # relative share among the top 5; NOT a calibrated probability
    return [(n, sc / total) for n, sc in ranked]


# --------------------------------------------------------------------------- Jev question builders
def _choice(instructions, criteria):
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def _domain_question(menu):
    counts = {}
    for s in menu["skills"].values():
        counts[s["domain"]] = counts.get(s["domain"], 0) + 1
    crit = dict((d, _trim(desc, 400)) for d, desc in menu["domains"].items() if counts.get(d))
    return _choice("Which domain does the task in the state belong to? Pick the single best match.", crit)


def _model_question():
    return _choice("Which model tier should execute this task? Pick the cheapest tier that will do it well.",
                   dict(MODEL_CRITERIA))


def _tools_question():
    return _choice("Which tool profile does executing this task need? Pick the smallest sufficient profile.",
                   dict(TOOLS_CRITERIA))


def _skill_questions(menu, names, desc_chars, hint_chars):
    """-> (questions, chunk_keys). <=254 skills: one `skill` Choice. More: `skill_1..skill_k`, each
    <=254 skills, ordered by (domain, name) so a chunk is thematically coherent. Every skill question ends
    with a `none` option (last key: "no listed skill fits").
    Criteria text is shrunk (description first) until every question fits MAX_QUESTION_CHARS."""
    dom_order = dict((d, i) for i, d in enumerate(menu["domains"]))
    ordered = sorted(names, key=lambda n: (dom_order.get(menu["skills"][n]["domain"], 99), n))
    if len(ordered) <= CHUNK_SKILLS:
        chunks = [ordered]
        chunked = False
    else:
        k = int(math.ceil(len(ordered) / float(CHUNK_SKILLS)))
        size = int(math.ceil(len(ordered) / float(k)))
        chunks = [ordered[i:i + size] for i in range(0, len(ordered), size)]
        chunked = True
    d_chars, h_chars = desc_chars, hint_chars
    while True:
        qs = {}
        keys = []
        total = 0
        worst = 0
        for ci, chunk in enumerate(chunks):
            crit = dict((n, _criteria_text(menu["skills"][n], d_chars, h_chars)) for n in chunk)
            crit[NONE_KEY] = NONE_TEXT  # always last
            instr = ("Which skill from this list best fits the task in the state? Pick the single best match, "
                     "or 'none' if no listed skill fits.")
            qname = "skill_%d" % (ci + 1) if chunked else "skill"
            qs[qname] = _choice(instr, crit)
            keys.append(qname)
            size = sum(len(k) + len(v) for k, v in crit.items())
            total += size
            worst = max(worst, size)
        if (worst <= MAX_QUESTION_CHARS and total <= MAX_TOTAL_CHARS) or d_chars <= MIN_DESC_CHARS:
            return qs, keys
        d_chars = max(MIN_DESC_CHARS, int(d_chars * 0.75))
        h_chars = max(MIN_DESC_CHARS, int(h_chars * 0.75))


def _merge_chunks(answers, chunk_keys):
    """p(skill) = p_chunk(skill) * (1 - p_chunk(none)), renormalised over all chunks.
    Returns (ranked [(skill, p)], min_none) where min_none = smallest p_chunk(none) across chunks
    (None when not chunked)."""
    raw = {}
    nones = []
    chunked = len(chunk_keys) > 1 or any(NONE_KEY in (answers[k].get("probabilities") or {}) for k in chunk_keys)
    for k in chunk_keys:
        probs = answers[k].get("probabilities") or {}
        p_none = float(probs.get(NONE_KEY, 0.0)) if chunked else 0.0
        if chunked:
            nones.append(p_none)
        for skill, p in probs.items():
            if skill == NONE_KEY:
                continue
            raw[skill] = float(p) * (1.0 - p_none)
    total = sum(raw.values())
    if total <= 0:  # every chunk said none with p=1: fall back to unweighted probabilities
        for k in chunk_keys:
            for skill, p in (answers[k].get("probabilities") or {}).items():
                if skill != NONE_KEY:
                    raw[skill] = float(p)
        total = sum(raw.values())
    if total <= 0:
        return [], (min(nones) if nones else None)
    ranked = sorted(((s, p / total) for s, p in raw.items()), key=lambda kv: (-kv[1], kv[0]))
    return ranked, (min(nones) if nones else None)


def _raw_ranked(answer):
    """Real skills of one skill question by RAW probability (the `none` mass is not renormalised away)."""
    probs = (answer or {}).get("probabilities") or {}
    return sorted(((s, float(p)) for s, p in probs.items() if s != NONE_KEY and float(p) > 0),
                  key=lambda kv: (-kv[1], kv[0]))


def _none_info(answers, keys):
    """-> (none_p, none_wins). none_p = smallest p(none) over the skill questions (the best chunk's view);
    none_wins = in EVERY skill question `none` beats the best real skill."""
    nones, wins = [], []
    for k in keys:
        probs = (answers.get(k) or {}).get("probabilities") or {}
        pn = float(probs.get(NONE_KEY, 0.0))
        best = max([float(p) for s, p in probs.items() if s != NONE_KEY] or [0.0])
        nones.append(pn)
        wins.append(pn > best)
    if not nones:
        return 0.0, False
    return round(min(nones), 4), all(wins)


def _none_fires(none_p, none_wins):
    return bool(none_wins) or (none_p or 0.0) >= NONE_T


def _gate_combined(domain_p, ranked):
    """Two-stage gate on the combined scale: p = domain_p * skill_p (raw stage-2 probabilities)."""
    if not ranked or domain_p is None:
        return "low_confidence"
    d = float(domain_p)
    p1 = d * ranked[0][1]
    p2 = d * (ranked[1][1] if len(ranked) > 1 else 0.0)
    return "pass" if (p1 >= TS_T1 and (p1 - p2) >= TS_T2) else "low_confidence"


def _best(answer, valid, default):
    tc = _jev().top_choices(answer, 1)
    if tc and tc[0][0] in valid:
        return tc[0][0]
    c = answer.get("choice") if isinstance(answer, dict) else None
    return c if c in valid else default


# --------------------------------------------------------------------------- selection + gate
def _select(ranked):
    """ranked [(skill, p)] desc -> (skills<=3, scores top-3, gate). The gate here is the FLAT gate (T1/T2);
    two-stage overrides it with _gate_combined."""
    if not ranked:
        return [], {}, "low_confidence"
    top1 = ranked[0][1]
    top2 = ranked[1][1] if len(ranked) > 1 else 0.0
    gate = "pass" if (top1 >= T1 and (top1 - top2) >= T2) else "low_confidence"
    skills = [ranked[0][0]]
    for n, p in ranked[1:MAX_SKILLS]:
        if p >= RANK_MIN_PROB:
            skills.append(n)
    scores = dict((n, round(p, 4)) for n, p in ranked[:MAX_SKILLS] if p > 0)
    return skills, scores, gate


def _apply_vi(skills, scores, menu):
    """Vietnamese pre-rule: map to -vi variants, drop EN-only writing skills. Returns (skills, scores)."""
    vi_map = menu.get("vi_map") or {}
    en_only = set(menu.get("en_only") or [])
    sk = menu["skills"]
    new_scores = {}
    for n, p in scores.items():
        t = vi_map.get(n, n)
        if t not in sk:
            t = n
        if t in en_only:
            continue
        new_scores[t] = min(1.0, new_scores.get(t, 0.0) + p)
    out = []
    for n in skills:
        t = vi_map.get(n, n)
        if t not in sk:
            t = n
        if t in en_only or t in out:
            continue
        out.append(t)
    if not out:  # everything was EN-only: content-polish handles both languages
        out = ["content-polish"] if "content-polish" in sk else list(skills)
        new_scores = dict(scores) if out == list(skills) else {out[0]: 1.0}
    return out, new_scores


# --------------------------------------------------------------------------- core routing
def _ask(text, questions, allow_jev, shadow, meta):
    jc = _jev()
    r = jc.ask(text, questions, PURPOSE, allow_jev=allow_jev, shadow=shadow, timeout=jc.DEFAULT_TIMEOUT)
    u = r.get("usage") or {}
    meta["input_tokens"] += int(u.get("input_tokens") or 0)
    meta["output_tokens"] += int(u.get("output_tokens") or 0)
    meta["usd"] += float(r.get("usd") or 0.0)
    meta["latency_ms"] += int(r.get("latency_ms") or 0)
    meta["calls"] += 1
    meta["routers"].append(r.get("router"))
    return r


def _grep_result(text, menu, names=None):
    ranked = grep_route(text, menu, names)
    skills = []
    if ranked:
        skills = [ranked[0][0]] + [n for n, p in ranked[1:MAX_SKILLS] if p >= RANK_MIN_PROB]
    scores = dict((n, round(p, 4)) for n, p in ranked[:MAX_SKILLS])
    return {"skills": skills, "model": GREP_DEFAULT_MODEL, "tools": GREP_DEFAULT_TOOLS, "scores": scores,
            "router": "grep", "gate": "low_confidence"}


def _jev_two_stage(text, menu, allow_jev, shadow, meta):
    r1 = _ask(text, {"domain": _domain_question(menu)}, allow_jev, shadow, meta)
    dom_ans = r1["answers"]["domain"]
    domain = dom_ans["choice"]
    domain_p = float((dom_ans.get("probabilities") or {}).get(domain, 0.0))
    meta["domain_p"] = round(domain_p, 4)
    names = [n for n, s in menu["skills"].items() if s["domain"] == domain or domain in (s.get("also") or ())]
    if not names:
        raise _jev().RouterUnavailable("domain %s has no routable skills" % domain)
    qs = {"model": _model_question(), "tools": _tools_question()}
    sq, skill_keys = _skill_questions(menu, names, TWO_STAGE_DESC_CHARS, TWO_STAGE_HINT_CHARS)
    qs.update(sq)  # asked even for a one-skill domain: `none` is always an option
    try:
        r2 = _ask(text, qs, allow_jev, shadow, meta)
    except _jev().RouterUnavailable:
        res = _grep_result(text, menu, names)  # stage 2 failed: grep restricted to the chosen domain
        res["domain"] = domain
        return res
    if len(skill_keys) == 1:
        ranked = _raw_ranked(r2["answers"][skill_keys[0]])
    else:
        ranked, _min_none = _merge_chunks(r2["answers"], skill_keys)
    none_p, none_wins = _none_info(r2["answers"], skill_keys)
    skills, scores, _flat_gate = _select(ranked)
    gate = _gate_combined(domain_p, ranked)  # real gate: domain uncertainty counts
    meta["skill_p"] = round(ranked[0][1], 4) if ranked else None
    meta["p_combined"] = round(domain_p * ranked[0][1], 4) if ranked else None
    meta["none_p"] = none_p
    meta["none_fired"] = _none_fires(none_p, none_wins)
    if meta["none_fired"]:
        skills, gate = [], "low_confidence"  # no listed skill fits: real candidates stay in scores as info
    return {"skills": skills, "model": _best(r2["answers"]["model"], MODEL_TIERS, GREP_DEFAULT_MODEL),
            "tools": _best(r2["answers"]["tools"], TOOL_PROFILES, GREP_DEFAULT_TOOLS), "scores": scores,
            "router": r2["router"], "gate": gate, "domain": domain}


def _jev_flat(text, menu, allow_jev, shadow, meta):
    names = list(menu["skills"])
    qs, keys = _skill_questions(menu, names, FLAT_DESC_CHARS, FLAT_HINT_CHARS)
    qs["model"] = _model_question()
    qs["tools"] = _tools_question()
    r = _ask(text, qs, allow_jev, shadow, meta)
    ranked, _min_none = _merge_chunks(r["answers"], keys)
    none_p, none_wins = _none_info(r["answers"], keys)
    skills, scores, gate = _select(ranked)
    meta["skill_p"] = round(ranked[0][1], 4) if ranked else None
    meta["none_p"] = none_p
    meta["none_fired"] = _none_fires(none_p, none_wins)
    if meta["none_fired"]:
        skills, gate = [], "low_confidence"  # even the best chunk says "none of these"
    domain = menu["skills"][skills[0]]["domain"] if skills else None
    return {"skills": skills, "model": _best(r["answers"]["model"], MODEL_TIERS, GREP_DEFAULT_MODEL),
            "tools": _best(r["answers"]["tools"], TOOL_PROFILES, GREP_DEFAULT_TOOLS), "scores": scores,
            "router": r["router"], "gate": gate, "domain": domain}


def _new_meta(mode):
    return {"input_tokens": 0, "output_tokens": 0, "usd": 0.0, "latency_ms": 0, "calls": 0, "routers": [],
            "mode": mode, "domain_p": None, "skill_p": None, "p_combined": None, "none_p": None,
            "none_fired": False}


def _core(text, menu, router, mode, shadow, meta):
    """The routing pipeline. Returns the contract dict (never raises except via MenuError upstream)."""
    names = list(menu["skills"])
    lang = detect_lang(text)
    pre_rules = []
    # 1. explicit /name passthrough (disabled in shadow: slash tokens are the answer there)
    if not shadow:
        explicit = slash_tokens(text, names)
        if explicit:
            explicit = explicit[:MAX_SKILLS]
            pre_rules.append("explicit")
            first = menu["skills"][explicit[0]]
            return {"skills": explicit, "model": PASSTHROUGH_MODEL, "tools": PASSTHROUGH_TOOLS,
                    "scores": dict((n, 1.0) for n in explicit), "domain": first["domain"],
                    "router": "passthrough", "gate": "pass", "pre_rules": pre_rules, "lang": lang,
                    "jev_down": _jev().is_down()}
    # 2. Vietnamese
    if lang == "vi":
        pre_rules.append("vietnamese")

    req = router if router in ROUTERS else DEFAULT_ROUTER
    use_mode = mode if mode in MODES else DEFAULT_MODE
    meta["mode"] = use_mode
    allow_jev = (req == "jev")
    res = None
    if not text.strip():
        res = {"skills": [], "model": GREP_DEFAULT_MODEL, "tools": GREP_DEFAULT_TOOLS, "scores": {},
               "router": "grep", "gate": "low_confidence", "domain": None}
    elif req != "grep":
        try:
            if use_mode == "flat":
                res = _jev_flat(text, menu, allow_jev, shadow, meta)
            else:
                res = _jev_two_stage(text, menu, allow_jev, shadow, meta)
        except Exception:
            res = None  # RouterUnavailable (incl. "disabled") or any client/shape surprise degrades to grep
    if res is None:
        res = _grep_result(text, menu)
    if "domain" not in res or res.get("domain") is None:
        res["domain"] = menu["skills"][res["skills"][0]]["domain"] if res["skills"] else None
    skills, scores = res["skills"], res["scores"]
    if lang == "vi" and skills:
        skills, scores = _apply_vi(skills, scores, menu)
    out = {"skills": skills, "model": res["model"], "tools": res["tools"], "scores": scores,
           "domain": res["domain"], "router": res["router"], "gate": res["gate"], "pre_rules": pre_rules,
           "lang": lang, "jev_down": _jev().is_down()}
    return out


def _contract_order(d):
    keys = ("skills", "model", "tools", "scores", "domain", "router", "gate", "pre_rules", "lang", "jev_down")
    return dict((k, d[k]) for k in keys)


def _excerpt(text):
    """Log excerpt: whitespace-squashed, credentials redacted, capped. Never the full text."""
    return _jev().redact(_squash(text))[:EXCERPT_CAP]


def _log_decision(text, project, res, meta):
    rec = {"ts": _now_iso(), "project": project, "text_excerpt": _excerpt(text), "mode": meta.get("mode"),
           "router": res["router"], "domain": res["domain"], "domain_p": meta.get("domain_p"),
           "skill_p": meta.get("skill_p"), "p_combined": meta.get("p_combined"), "none_p": meta.get("none_p"),
           "none_fired": bool(meta.get("none_fired")),
           "skills": res["skills"], "scores": res["scores"], "model": res["model"], "tools": res["tools"],
           "gate": res["gate"], "lang": res["lang"], "pre_rules": res["pre_rules"],
           "jev_down": res["jev_down"], "calls": meta["calls"], "input_tokens": meta["input_tokens"],
           "usd": round(meta["usd"], 8), "latency_ms": meta["latency_ms"]}
    _append_jsonl(_decision_log_path(), rec)


def _route_full(text, project, router, mode, log, shadow=False):
    menu = load_menu(strict=False)  # MenuError propagates (fail loud); unassigned skills are not fatal here
    meta = _new_meta(mode if mode in MODES else DEFAULT_MODE)
    text = text if isinstance(text, str) else str(text or "")
    try:
        res = _core(text, menu, router, mode, shadow, meta)
    except MenuError:
        raise
    except Exception:
        res = _contract_order(dict(_grep_result(text, menu), domain=None, pre_rules=[], lang=detect_lang(text),
                                   jev_down=False))
        if res["skills"]:
            res["domain"] = menu["skills"][res["skills"][0]]["domain"]
    res = _contract_order(res)
    if log:
        _log_decision(text, project, res, meta)
    return res, meta


def route(text, project=None, router=None, mode=None, log=True, cwd=None):
    """Route a task text. Returns the contract dict. Never prints; raises only MenuError.
    `project` is recorded in the decision log; `cwd` is accepted for API compatibility and unused."""
    res, _meta = _route_full(text, project, router, mode, log)
    return res


# --------------------------------------------------------------------------- shadow
_SKILLS_LINE_RE = re.compile(r"(?im)^[ \t>*-]*skills?(?:[ \t]+to[ \t]+(?:load|use))?[ \t]*:[ \t]*(.*)$")


def _actual_skills(prompt, names):
    lower = dict((n.lower(), n) for n in names)
    out = []
    for m in _SKILLS_LINE_RE.finditer(prompt or ""):
        for tok in re.split(r"[\s,;]+", m.group(1)):
            tok = tok.strip().lstrip("/").strip("`'\".()[]")
            n = lower.get(tok.lower())
            if n and n not in out:
                out.append(n)
    for n in slash_tokens(prompt, names):
        if n not in out:
            out.append(n)
    return out


def shadow_run(raw):
    """One --shadow record (stdin JSON {prompt, description, spawn_id, subagent_type, parent_agent}).
    Never raises; prints nothing."""
    try:
        warnings.simplefilter("ignore")  # shadow prints NOTHING, stderr included
        if os.environ.get("SKILL_ROUTE_CHILD") == "1":
            return
        if os.path.exists(_shadow_off_path()):
            return
        try:
            data = json.loads(raw) if raw and raw.strip() else {}
        except ValueError:
            return
        if not isinstance(data, dict):
            return
        menu = load_menu(strict=False)
        names = list(menu["skills"])
        prompt = str(data.get("prompt") or "")
        desc = str(data.get("description") or "")
        actual = _actual_skills(prompt, names)
        body = _SKILLS_LINE_RE.sub("", prompt)
        full = strip_slash_tokens(desc + "\n" + body, names).strip()
        text = full[:SHADOW_TEXT_CAP]
        res, _meta = _route_full(text, None, None, None, False, shadow=True)
        rs = res["skills"]
        if actual:
            agree1 = bool(rs) and rs[0] in actual
            agree_any = any(s in actual for s in rs)
        else:
            agree1 = agree_any = None
        _append_jsonl(_shadow_log_path(), {
            "ts": _now_iso(), "spawn_id": data.get("spawn_id"), "subagent_type": data.get("subagent_type"),
            "parent_agent": data.get("parent_agent"), "task_excerpt": _excerpt(text),
            "actual_skills": actual, "router_skills": rs, "router": res["router"], "domain": res["domain"],
            "gate": res["gate"], "agree_top1": agree1, "agree_any": agree_any})
    except Exception:
        return


def _read_jsonl(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
    except OSError:
        pass
    return out


def shadow_report():
    recs = _read_jsonl(_shadow_log_path())
    usage = _read_jsonl(_usage_log_path())
    lines = ["skill-route shadow report", "log: %s" % _shadow_log_path()]
    lines.append("window start: %s" % (recs[0].get("ts") if recs else "n/a (no records)"))
    withact = [r for r in recs if r.get("actual_skills")]
    lines.append("records: %d" % len(recs))
    lines.append("records with actual skills: %d" % len(withact))

    def pct(num, den):
        return "n/a" if not den else "%.1f%% (%d/%d)" % (100.0 * num / den, num, den)

    lines.append("top-1 agreement: %s" % pct(sum(1 for r in withact if r.get("agree_top1")), len(withact)))
    lines.append("any agreement:   %s" % pct(sum(1 for r in withact if r.get("agree_any")), len(withact)))
    by = {}
    for r in recs:
        by.setdefault(r.get("router") or "?", []).append(r)
    lines.append("by router:")
    for k in sorted(by):
        w = [r for r in by[k] if r.get("actual_skills")]
        lines.append("  %-6s records %d, with actual %d, top-1 %s, any %s" % (
            k, len(by[k]), len(w), pct(sum(1 for r in w if r.get("agree_top1")), len(w)),
            pct(sum(1 for r in w if r.get("agree_any")), len(w))))
    sh = [u for u in usage if u.get("shadow") is True]
    jev_usd = sum(float(u.get("usd") or 0) for u in sh if u.get("router") == "jev")
    hk_usd = sum(float(u.get("usd") or 0) for u in sh if u.get("router") == "haiku")
    jev_n = sum(1 for u in sh if u.get("router") == "jev" and u.get("ok"))
    jev_tok = sum(int(u.get("input_tokens") or 0) for u in sh if u.get("router") == "jev")
    lines.append("Jev cost to date (shadow calls): $%.6f over %d ok calls, %d input tokens" % (jev_usd, jev_n, jev_tok))
    lines.append("Haiku fallback cost to date (shadow calls, shown separately): $%.6f" % hk_usd)
    by_p = {}
    for u in sh:
        if u.get("router") == "jev":
            by_p[u.get("purpose") or "?"] = by_p.get(u.get("purpose") or "?", 0.0) + float(u.get("usd") or 0)
    if by_p:
        lines.append("  Jev shadow usd by purpose: " + ", ".join("%s $%.6f" % (k, by_p[k]) for k in sorted(by_p)))
    print("\n".join(lines))


# --------------------------------------------------------------------------- CLI
def _build_parser():
    p = argparse.ArgumentParser(prog="skill-route.py",
                                description="Jev skill router (off unless AGENCY_SKILL_ROUTER=1).")
    p.add_argument("text", nargs="*", help="task text (or pass it on stdin)")
    p.add_argument("--project", default=None, help="project slug, recorded in the decision log")
    p.add_argument("--router", choices=ROUTERS, default=None, help="jev (default) | haiku | grep")
    p.add_argument("--mode", choices=MODES, default=None, help="two-stage (default) | flat")
    p.add_argument("--no-log", action="store_true", help="skip the decision log skill-route.jsonl")
    p.add_argument("--rebuild-menu", action="store_true", help="rebuild the menu cache")
    p.add_argument("--shadow", action="store_true", help="shadow mode: stdin JSON, logs, prints nothing")
    p.add_argument("--shadow-report", action="store_true", help="print the shadow agreement/cost report")
    return p


WARN_NAMES_MAX = 10


def _unassigned_warning(unassigned):
    """The ONE stderr line main() prints when skills have no overlay entry (lenient runtime). None if none."""
    if not unassigned:
        return None
    shown = ", ".join(unassigned[:WARN_NAMES_MAX]) + (", ..." if len(unassigned) > WARN_NAMES_MAX else "")
    add = shlex.quote(os.path.join(_scripts_dir(), "skill-route-overlay-add.py"))
    return ("skill-route.py: warning: %d skill(s) have no overlay entry and are not routable: %s. "
            "Fix: python3 %s NAME [--domain D --hint H]" % (len(unassigned), shown, add))


def main(argv=None):
    if not router_enabled():
        # FIRST, whatever the arguments: no stdin read, no file write, no jev_client import, no network.
        sys.stdout.write(DISABLED_LINE + "\n")
        sys.stdout.flush()
        return 0
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--shadow" in args_list:
        # shadow must never raise or print, whatever else is on the command line
        try:
            raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        except Exception:
            raw = ""
        shadow_run(raw)
        return 0
    try:
        args = _build_parser().parse_args(args_list)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2
    if args.shadow_report:
        shadow_report()
        return 0
    try:
        text = " ".join(args.text).strip()
        if not text and not args.rebuild_menu and not sys.stdin.isatty():  # --rebuild-menu alone never waits on stdin
            text = sys.stdin.read().strip()
        if not text and not args.rebuild_menu:
            sys.stderr.write("skill-route.py: no task text (pass TEXT or stdin)\n")
            return 2
        # Runtime is lenient: unassigned skills are excluded and warned about once; route() reloads from the cache.
        menu = load_menu(rebuild=args.rebuild_menu, strict=False)
        warning = _unassigned_warning(menu.get("unassigned"))
        if warning:
            sys.stderr.write(warning + "\n")
        if not text:  # --rebuild-menu alone: print the menu stats and stop
            print(json.dumps(menu_stats(menu), ensure_ascii=False))
            return 0
        res = route(text, project=args.project, router=args.router, mode=args.mode,
                    log=not args.no_log, cwd=os.getcwd())
    except MenuError as e:
        sys.stderr.write("skill-route.py: MenuError: %s\n" % e)
        return 2
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
