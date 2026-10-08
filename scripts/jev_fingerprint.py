"""jev_fingerprint.py - content fingerprint of everything that decides what the Jev router does.

One fingerprint = sha256 over (a) the AST of skill-route.py and jev_client.py and (b) the ROUTABLE skill menu
skill-route.py builds. The eval/drill writers stamp it into their result files ("inputs_fingerprint"); the
gate check (jev-gate-check.py) recomputes it and counts a result only when the two are equal.

Counts:  non-comment, non-docstring code of the two scripts; per routable skill name, description, triggers
         (INDEX.catalog.json), domain, also_domains, hint; the overlay domains, vi_map and en_only.
Ignored: comments, docstrings, formatting, mtimes, built_at / sig, and every excluded skill (an `exclude` overlay
         entry never reaches the router). Same interpreter version assumed: ast.dump differs across Python versions.

Offline: building the fingerprint loads skill-route.py as a module and builds its menu; it makes no network call
and does not depend on the AGENCY_SKILL_ROUTER switch.

Stdlib only; Python 3.9 compatible. Env vars SKILL_ROUTE_SKILLS_DIR / SKILL_ROUTE_OVERLAY / SKILL_ROUTE_STATE_DIR flow
through to skill-route.py's own menu builder untouched.
"""
import ast
import hashlib
import importlib.util
import itertools
import json
import os

SCRIPTS_DEFAULT = os.path.dirname(os.path.abspath(__file__))
CODE_FILES = ("skill-route.py", "jev_client.py")
_SEQ = itertools.count(1)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return tree


def code_digest(path):
    """sha256 of the docstring-free AST dump (no comments, formatting or positions). Unparseable file: sha256 of its bytes."""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        tree = _strip_docstrings(ast.parse(raw, filename=path))
        return _sha(ast.dump(tree, include_attributes=False).encode("utf-8"))
    except (SyntaxError, ValueError):
        return _sha(raw)


def menu_digest(menu):
    """sha256 of the router-visible menu: routable skills + domains + vi_map + en_only. Never built_at, sig or excluded."""
    skills = [{"name": n, "description": s.get("description"), "triggers": s.get("triggers"), "domain": s.get("domain"),
               "also": s.get("also"), "hint": s.get("hint")} for n, s in sorted(menu["skills"].items())]
    doc = {"skills": skills, "domains": menu.get("domains"), "vi_map": menu.get("vi_map"), "en_only": menu.get("en_only")}
    return _sha(json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def inputs_fingerprint(scripts_dir=None):
    """'sha256:<hex>' over the code digests + the freshly built routable menu. MenuError (or any build error) propagates."""
    base = scripts_dir or SCRIPTS_DEFAULT
    path = os.path.join(base, "skill-route.py")
    spec = importlib.util.spec_from_file_location("jev_fp_skill_route_%d" % next(_SEQ), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    menu = mod.load_menu(rebuild=True)
    parts = []
    for fn in CODE_FILES:
        p = os.path.join(base, fn)
        parts.append("%s=%s" % (fn, code_digest(p) if os.path.isfile(p) else "missing"))
    parts.append("menu=" + menu_digest(menu))
    return "sha256:" + _sha("\n".join(parts).encode("utf-8"))


def fingerprint_fields(scripts_dir=None):
    """Result-file fields for a writer. Never raises: on any error {"inputs_fingerprint": None, "inputs_fingerprint_error": msg}."""
    try:
        return {"inputs_fingerprint": inputs_fingerprint(scripts_dir)}
    except (Exception, SystemExit) as e:
        return {"inputs_fingerprint": None,
                "inputs_fingerprint_error": "%s: %s" % (e.__class__.__name__, " ".join(str(e).split()))}
