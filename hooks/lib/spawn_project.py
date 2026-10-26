"""spawn_project.py: ONE place that maps a spawn to its project and its spawns.jsonl.

Shared by mods/spawn-ledger/bin/ledger.py (writer) and hooks/lib/model-pin.py (model pin + Exec cap policy: reads the logs for the
Exec cap, appends model_override / spawn_denied rows), so both pick the same file for the same spawn. stdlib only.
NEVER raises: every failure degrades to the global log <root>/logs/spawns.jsonl
(<root> = AGENCY_HOME, else CLAUDE_CONFIG_DIR, else ~/.claude; see hooks/lib/resolve-root.sh).

Resolution order (scripts/skill-route.py _spawn_project calls this module, so there is one implementation):
  0. env SPAWN_LOG_FILE (tests / explicit override) wins over everything
  1. a `Project:` line in the prompt: a path on it -> longest-prefix match with path-boundary check, else its first
     word if that is a table slug
  2. data.parent_agent `{slug}-pd`
  3. data.subagent_type `{slug}-pd`
  4. CLAUDE_PROJECT_DIR (else cwd) -> longest-prefix match with path-boundary check
  5. the global log
A slug / path that is not in the table falls through to the next step. The log is `{root}/memory/spawns.jsonl`.

Table: the Active Projects rows of memory/medium-term.md (`| slug | `path` | ...`). Test overrides: env
SPAWN_MEDIUM_TERM (table path), env SPAWN_LEDGER_EXTRA_LOGS (os.pathsep list; the ONLY extra logs when SPAWN_LOG_FILE
is set), and every function that touches `~` takes home= (default: expanduser("~")).
Only a LEADING ~ is expanded; `/x/a~b` is a plain path.
Windows: roots / paths in any of C:\\x, C:/x, c:\\X (case-folded), \\\\unc, ~\\x and the Git-Bash spellings /c/x, /mnt/c/x,
/cygdrive/c/x compare equal; the Git-Bash fold applies only when a drive path is on one side. A log path is returned in the
OS spelling (_native). scripts/skill-route.py and hooks/lib/resolve-project.sh reuse this module; they do not match paths.
"""
import glob
import os
import re


def _home(home=None):
    return home or os.path.expanduser("~")


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


# ponytail: win32 paths (C:\x, C:/x, \\unc, ~\x) are folded to "/" form before any comparison; a plain POSIX string
# (which may legally hold a backslash) is never touched. UNC case stays exact; only drive-letter paths casefold.
_WINISH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|~\\)")
_DRIVE = re.compile(r"^[A-Za-z]:/")
# Git-Bash / WSL / Cygwin spellings of a drive path: /d/x, /mnt/d/x, /cygdrive/d/x. They only ever mean a drive when the
# OTHER side of a comparison is a drive path (or the OS is Windows): a bare POSIX /d/x with no drive in sight stays as is.
_MSYS = re.compile(r"^/(?:(?:mnt|cygdrive)/)?([A-Za-z])(?:/|$)")


def _norm(p):
    if isinstance(p, str) and _WINISH.match(p):
        return p.replace("\\", "/").rstrip("/")
    return p


def _drive(p):
    """/d/x, /mnt/d/x, /cygdrive/d/x -> D:/x; anything else unchanged."""
    m = _MSYS.match(p)
    return "%s:/%s" % (m.group(1).upper(), p[m.end():]) if m else p


_SEP = os.sep


def _native(p):
    """File-path spelling of a root: backslashes where the OS separator is one, else untouched (POSIX is byte-identical).
    project_rows() keeps the "/"-folded form (its documented contract, hooks/tests/test_win32_model_pin.py) and matching
    folds the same way; joining that onto "memory", "spawns.jsonl" with os.path.join built C:/x/alpha\\memory\\spawns.jsonl on
    Windows (two spellings of one file). Every path this module RETURNS for a file goes through here."""
    return _drive(p).replace("/", "\\") if _SEP == "\\" else p


def _expand(path, home):
    if path == "~" or path.startswith("~/"):
        return home + path[1:]
    if path.startswith("~\\"):
        return home + "/" + path[2:].replace("\\", "/")
    return path


def global_log(home=None):
    return os.path.join(agency_root(_home(home)), "logs", "spawns.jsonl")


def medium_term_path(home=None):
    return os.environ.get("SPAWN_MEDIUM_TERM") or os.path.join(agency_root(_home(home)), "memory", "medium-term.md")


def project_rows(home=None, path=None):
    """[(slug, root)] from the medium-term table (trailing / and /memory stripped, leading ~ expanded).
    path= reads that table instead of medium_term_path() (scripts/skill-route.py SKILL_ROUTE_MEDIUM_TERM).
    Raises on a missing/unreadable table; callers that must not raise catch."""
    h = _home(home)
    rows = []
    with open(path or medium_term_path(h), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\|\s*([^|`]+?)\s*\|\s*`([^`]+)`", line)
            if not m:
                continue
            raw = _norm(_expand(m.group(2).strip(), h)).rstrip("/")
            root = (raw[:-7] if raw.endswith("/memory") else raw).rstrip("/")
            if root:
                rows.append((m.group(1).strip(), root))
    return rows


def longest_prefix(path, rows):
    """Slug of the row whose root is the longest path-boundary prefix of `path` (/x/alphabet is NOT under /x/alpha)."""
    path = _norm(path or "").rstrip("/") or "/"
    best_len, best = 0, None
    for slug, root in rows:
        root = _norm(root)
        p, r = path, root
        if _DRIVE.match(root) or _DRIVE.match(path):  # a drive path on either side: fold msys spellings, ignore case
            p, r = _drive(path).casefold(), _drive(root).casefold()
        if (p == r or p.startswith(r + "/")) and len(r) > best_len:
            best_len, best = len(r), slug
    return best


def pd_slug(name, slugs):
    """`{slug}-pd` -> slug when the slug is in the table, else None."""
    if isinstance(name, str) and name.endswith("-pd") and name[:-3] in slugs:
        return name[:-3]
    return None


def spawn_project(data=None, prompt=None, home=None, rows=None):
    """Project slug of a spawn per the order in the module docstring, or None (= global). Never raises.
    prompt defaults to data["prompt"]. No args = steps 4-5 only. rows= a project_rows() result the caller already has."""
    try:
        h = _home(home)
        rows = project_rows(h) if rows is None else rows
    except Exception:
        return None
    try:
        data = data if isinstance(data, dict) else {}
        if prompt is None:
            prompt = data.get("prompt")
        slugs = set(s for s, _ in rows)
        for m in re.finditer(r"(?im)^[ \t]*project:[ \t]*(.*)$", prompt if isinstance(prompt, str) else ""):
            val = m.group(1)
            for pm in re.finditer(r"(~?/[^\s`'\",;)\]]*|(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s`'\",;)\]]*|~\\[^\s`'\",;)\]]*)", val):
                hit = longest_prefix(_expand(pm.group(1), h), rows)
                if hit:
                    return hit
            first = (val.split() or [""])[0].strip("`'\",;")
            if first in slugs:
                return first
        for key in ("parent_agent", "subagent_type"):
            hit = pd_slug(data.get(key), slugs)
            if hit:
                return hit
        return longest_prefix(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(), rows)
    except Exception:
        return None


def resolve_log_file(data=None, home=None):
    """spawns.jsonl for this spawn (see module docstring). data = {prompt, subagent_type, parent_agent, ...} or None."""
    try:
        override = os.environ.get("SPAWN_LOG_FILE", "")
        if override:
            return override
        h = _home(home)
        slug = spawn_project(data, None, h)
        if slug:
            root = dict(project_rows(h)).get(slug)
            if root:
                return os.path.join(_native(root), "memory", "spawns.jsonl")
        return global_log(h)
    except Exception:
        return global_log(home)


def all_logs(primary, home=None):
    """Every other spawns.jsonl a spawn row may sit in (existing files only, deduped by abspath, `primary` excluded):
    the global log, each medium-term project log, projects/*/memory/spawns.jsonl. With SPAWN_LOG_FILE set (tests)
    only SPAWN_LEDGER_EXTRA_LOGS. Never raises."""
    cands = []
    try:
        if os.environ.get("SPAWN_LOG_FILE"):
            cands += [x for x in os.environ.get("SPAWN_LEDGER_EXTRA_LOGS", "").split(os.pathsep) if x]
        else:
            h = _home(home)
            cands.append(global_log(h))
            try:
                cands += [os.path.join(_native(root), "memory", "spawns.jsonl") for _slug, root in project_rows(h)]
            except Exception:
                pass
            cands += sorted(glob.glob(os.path.join(agency_root(h), "projects", "*", "memory", "spawns.jsonl")))
    except Exception:
        pass
    seen, out = {os.path.abspath(primary)}, []
    for c in cands:
        try:
            a = os.path.abspath(c)
            if a not in seen and os.path.isfile(a):
                seen.add(a)
                out.append(a)
        except Exception:
            pass
    return out
