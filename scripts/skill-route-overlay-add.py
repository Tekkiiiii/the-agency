#!/usr/bin/env python3
"""skill-route-overlay-add.py - add a skill-route overlay entry for a newly installed skill.

Why: a skill directory with no entry in overlay.json is left out of the router menu
(skill-route.py warns on stderr; CI's check-skill-route-menu.py and
`jev-gate-check.py --only menu-build` treat it as a FAIL). This helper adds the entry
safely and idempotently. It is offline (no network, no router import) and works whether
or not the router is enabled.

Usage:
  skill-route-overlay-add.py NAME [--domain D --hint H] [--why W]

  NAME            skill directory name (non-empty, no "/", not starting with "." or "_")
  --domain D      make the skill routable; D must be a key of overlay["domains"]
  --hint H        routing hint (needs --domain); omitted from the entry if not given
  --why W         why text; overrides the default for the exclude entry, and is
                  included in a routable entry only when given

Entries written:
  default        {"exclude": "internal", "why": "auto-added on install YYYY-MM-DD; add domain+hint to make it routable"}
  with --domain  {"domain": D, "hint": H}  (+ "why" only if --why given)

Behaviour:
  - Idempotent: if skills[NAME] already exists it is never touched or overwritten, and the file
    (bytes and mtime) is not rewritten. A well-formed entry prints "exists: NAME", exit 0. An entry
    that skill-route.py _build_menu would still reject (not an object; neither "exclude" nor
    "domain"; unknown domain; unknown also_domains) prints "exists (invalid entry: <why>): NAME"
    to stderr and exits 1: repair it by hand.
  - New key is inserted at its sorted position when the existing skills keys are
    sorted, else appended. Every other byte of the file is preserved (indent,
    ensure_ascii and trailing newline are detected from the existing file).
  - Atomic write: temp file in the same dir + os.replace; file mode preserved. A symlinked
    overlay is resolved (os.path.realpath) first, so the link survives and its target is rewritten.
  - Concurrency: load -> modify -> replace runs under fcntl.flock(LOCK_EX) on a sidecar lock file
    <SKILL_ROUTE_STATE_DIR or {root}/state/skill-route>/overlay-add-<sha1 of realpath>.lock (created if
    missing, never deleted; state/ is git-ignored, a lock next to overlay.json would not be).
    {root} is the agency root: AGENCY_HOME, else CLAUDE_CONFIG_DIR, else the default config dir under $HOME.
    If that dir is unusable it falls back to tempfile.gettempdir(); if no lock can be taken at
    all it proceeds unlocked and says so on stderr (it never fails the caller).
  - Limitation: the file is re-serialised with json.dumps, so a mixed-escape file (some raw
    non-ASCII, some \\uXXXX escapes) is normalised to one style; everything else is preserved.

Env:
  SKILL_ROUTE_OVERLAY   overlay path; default <dir of this script>/skill-route/overlay.json
                        (same rule as skill-route.py `_overlay_path`)

Exit codes:
  0  added or exists (well-formed)
  2  usage / validation error (bad NAME, unknown domain, --hint without --domain)
  1  overlay unreadable / not a JSON object / missing "skills" dict / existing entry invalid

Importable (load with importlib.util.spec_from_file_location; the filename has dashes):
  add_entry(name, domain=None, hint=None, why=None, overlay_path=None) -> (status, entry)
  status is "added", "exists" or "invalid" (existing entry is malformed; entry is returned
  as found, nothing written); raises ValueError on validation errors and OverlayError on an
  unreadable/invalid overlay. entry_problem(entry, domains) -> reason string or None.

NOTE: jev-gate-check.py judges eval/drill staleness by content hash (jev_fingerprint.py).
An exclude-only addition (the default here) or any touch of overlay.json does NOT stale
the results. Adding a routable entry (--domain), or changing a routable skill's
description/triggers/domain/hint or the router code, does; re-run the commands the gate
prints (eval / drill) after such a change.

Stdlib only; Python 3.9 compatible.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile

try:
    import fcntl
except ImportError:  # non-POSIX: no locking available, helper still works
    fcntl = None


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


class OverlayError(Exception):
    """Overlay file unreadable or structurally invalid."""


def overlay_path():
    return os.environ.get("SKILL_ROUTE_OVERLAY") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "skill-route", "overlay.json")


def validate_name(name):
    if not isinstance(name, str) or not name or name.strip() != name:
        raise ValueError("invalid skill name %r: must be non-empty without surrounding whitespace" % (name,))
    if "/" in name:
        raise ValueError("invalid skill name %r: must not contain '/'" % name)
    if name[0] in "._":
        raise ValueError("invalid skill name %r: names starting with '.' or '_' are ignored by skill-route" % name)


def _detect_format(text):
    indent = 1
    for line in text.splitlines():
        m = re.match(r"^([ \t]+)\S", line)
        if m:
            ws = m.group(1)
            indent = "\t" if ws[0] == "\t" else len(ws)
            break
    ensure_ascii = all(ord(c) < 128 for c in text)
    return indent, ensure_ascii, text.endswith("\n")


def _load(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
        data = json.loads(text)
    except (OSError, ValueError) as e:  # UnicodeDecodeError and JSONDecodeError are ValueErrors
        raise OverlayError("cannot read overlay %s: %s" % (path, e))
    if not isinstance(data, dict):
        raise OverlayError("overlay %s is not a JSON object" % path)
    if not isinstance(data.get("skills"), dict):
        raise OverlayError('overlay %s has no "skills" object' % path)
    return text, data


def _atomic_write(path, content):
    directory = os.path.dirname(os.path.abspath(path))
    mode = os.stat(path).st_mode & 0o7777
    fd, tmp = tempfile.mkstemp(prefix=".overlay-add-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def entry_problem(ov, domains):
    """Why skill-route.py _build_menu would reject this existing skills[NAME] entry, or None if it accepts it.

    Replicates the four per-skill checks of _build_menu (scripts/skill-route.py); nothing is imported from it.
    """
    if not isinstance(ov, dict):                                    # 1. entry is not an object
        return "not an object"
    if ov.get("exclude"):                                           # excluded entries stop here in _build_menu
        return None
    dom = ov.get("domain")
    if not dom:                                                     # 2. "no domain"
        return "no 'exclude' or 'domain'"
    domains = domains if isinstance(domains, dict) else {}
    try:
        if dom not in domains:                                      # 3. "unknown domain"
            return "unknown domain %r" % (dom,)
        also = [d for d in (ov.get("also_domains") or []) if d != dom]
        bad = [d for d in also if d not in domains]
    except TypeError:
        return "unknown also_domains (not a list of domain names)" if dom in domains else "unknown domain %r" % (dom,)
    if bad:                                                         # 4. "unknown also_domains"
        return "unknown also_domains %r" % (bad,)
    return None


def _lock_candidates(real):
    name = "overlay-add-%s.lock" % hashlib.sha1(real.encode("utf-8")).hexdigest()[:16]
    state = os.environ.get("SKILL_ROUTE_STATE_DIR") or os.path.join(
        agency_root(os.path.expanduser("~")), "state", "skill-route")
    return [os.path.join(state, name), os.path.join(tempfile.gettempdir(), name)]


@contextlib.contextmanager
def _locked(real):
    """Exclusive flock on a sidecar lock file for the whole read-modify-write. Never raises because of the lock."""
    fh = None
    if fcntl is not None:
        for lock_path in _lock_candidates(real):
            try:
                os.makedirs(os.path.dirname(lock_path), exist_ok=True)
                fh = open(lock_path, "a")
                fcntl.flock(fh, fcntl.LOCK_EX)
                break
            except OSError:
                if fh is not None:
                    fh.close()
                    fh = None
    if fh is None:
        print("warning: skill-route-overlay-add: proceeding without a lock for %s" % real, file=sys.stderr)
    try:
        yield
    finally:
        if fh is not None:
            fh.close()      # closing the descriptor releases the flock


def add_entry(name, domain=None, hint=None, why=None, overlay_path=None):
    """Add skills[name] to the overlay. Returns ("added"|"exists"|"invalid", entry)."""
    status, entry, _problem = add_entry_full(name, domain, hint, why, overlay_path)
    return status, entry


def add_entry_full(name, domain=None, hint=None, why=None, overlay_path=None):
    """Like add_entry, but returns (status, entry, problem); problem is the reason when status is "invalid"."""
    validate_name(name)
    if hint is not None and domain is None:
        raise ValueError("--hint requires --domain")
    path = os.path.realpath(overlay_path or globals()["overlay_path"]())
    with _locked(path):
        return _add_locked(path, name, domain, hint, why)


def _add_locked(path, name, domain, hint, why):
    text, data = _load(path)

    if domain is not None:
        domains = data.get("domains")
        valid = sorted(domains) if isinstance(domains, dict) else []
        if domain not in valid:
            raise ValueError("unknown domain %r; valid domains: %s" % (domain, ", ".join(valid)))

    skills = data["skills"]
    if name in skills:
        problem = entry_problem(skills[name], data.get("domains"))
        return ("invalid" if problem else "exists"), skills[name], problem

    if domain is None:
        entry = {
            "exclude": "internal",
            "why": why if why is not None else (
                "auto-added on install %s; add domain+hint to make it routable"
                % datetime.date.today().isoformat()),
        }
    else:
        entry = {"domain": domain}
        if hint is not None:
            entry["hint"] = hint
        if why is not None:
            entry["why"] = why

    keys = list(skills)
    if keys == sorted(keys):
        items = list(skills.items())
        pos = len(items)
        for i, (k, _) in enumerate(items):
            if k > name:
                pos = i
                break
        items.insert(pos, (name, entry))
        data["skills"] = dict(items)
    else:
        skills[name] = entry

    indent, ensure_ascii, trailing_nl = _detect_format(text)
    out = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
    if trailing_nl:
        out += "\n"
    _atomic_write(path, out)
    return "added", entry, None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill-route-overlay-add.py",
                                 description="Add a skill-route overlay entry for a newly installed skill.")
    ap.add_argument("name")
    ap.add_argument("--domain")
    ap.add_argument("--hint")
    ap.add_argument("--why")
    args = ap.parse_args(argv)  # argparse exits 2 on usage errors
    try:
        status, _, problem = add_entry_full(args.name, domain=args.domain, hint=args.hint, why=args.why)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    except OverlayError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    if status == "invalid":
        print("exists (invalid entry: %s): %s" % (problem, args.name), file=sys.stderr)
        return 1
    print("%s: %s" % (status, args.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
