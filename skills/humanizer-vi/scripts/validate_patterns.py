#!/usr/bin/env python3
"""Validate patterns/humanizer.yml against patterns/schema.json.

Uses `jsonschema` when importable; otherwise falls back to an explicit checker
covering the parts of the schema that actually constrain this catalog.
Only dependency is PyYAML. Exits 0 on success, 1 on validation failure.
"""

import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YML = os.path.join(ROOT, "patterns", "humanizer.yml")
SCHEMA = os.path.join(ROOT, "patterns", "schema.json")

REQUIRED = [
    "id", "name", "skill", "category", "finding_type", "scope", "aggregation",
    "severity", "confidence", "summary", "signals", "why_it_matters",
    "rewrite_strategy", "bad_examples", "good_examples", "exceptions",
    "false_positive_risk", "tags",
]
OPTIONAL = ["min_occurrences", "case_sensitive"]
ENUMS = {
    "skill": {"humanizer-vi", "translationese-cleaner-vi", "grammar-checker-vi",
              "style-guide-vi"},
    "finding_type": {"error", "warning", "preference", "heuristic"},
    "scope": {"token", "phrase", "sentence", "paragraph", "document"},
    "aggregation": {"single", "count", "density", "sequence", "variance",
                    "consistency"},
    "severity": {"low", "medium", "high"},
    "confidence": {"low", "medium", "high"},
    "false_positive_risk": {"low", "medium", "high"},
}
ID_RE = re.compile(r"^VI-(HUM|TRA|GRA|STY)-[A-Z][0-9]{2}$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SIGNAL_KEYS = {"phrases", "regex", "exclude_phrases"}
GOOD_MODES = {"clean_rewrite", "review_comment", "needs_author_decision",
              "no_change"}


def explicit_check(doc):
    errs = []
    if doc.get("schema_version") != "1.0":
        errs.append("schema_version must be '1.0'")
    patterns = doc.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        errs.append("patterns must be a non-empty array")
        return errs
    seen = {}
    for i, p in enumerate(patterns):
        tag = p.get("id", "<index %d>" % i)
        if not isinstance(p, dict):
            errs.append("%s: not a mapping" % tag)
            continue
        for k in REQUIRED:
            if k not in p:
                errs.append("%s: missing required key '%s'" % (tag, k))
        for k in p:
            if k not in REQUIRED and k not in OPTIONAL:
                errs.append("%s: unexpected key '%s' (additionalProperties=false)"
                            % (tag, k))
        if not ID_RE.match(str(p.get("id", ""))):
            errs.append("%s: id fails ^VI-(HUM|TRA|GRA|STY)-[A-Z][0-9]{2}$" % tag)
        if p.get("id") in seen:
            errs.append("%s: duplicate id (also at index %d)" % (tag, seen[p["id"]]))
        seen[p.get("id")] = i
        if not KEBAB_RE.match(str(p.get("name", ""))):
            errs.append("%s: name '%s' is not kebab-case ascii"
                        % (tag, p.get("name")))
        for k, allowed in ENUMS.items():
            if k in p and p[k] not in allowed:
                errs.append("%s: %s='%s' not in %s"
                            % (tag, k, p[k], sorted(allowed)))
        if len(str(p.get("category", ""))) < 2:
            errs.append("%s: category too short" % tag)
        for k in ("summary", "why_it_matters"):
            if len(str(p.get(k, ""))) < 12:
                errs.append("%s: %s shorter than 12 chars" % (tag, k))
        sig = p.get("signals")
        if not isinstance(sig, dict) or not sig:
            errs.append("%s: signals must be a non-empty mapping" % tag)
        else:
            for k, v in sig.items():
                if k not in SIGNAL_KEYS:
                    errs.append("%s: signals has unexpected key '%s'" % (tag, k))
                elif not isinstance(v, list) or not v:
                    errs.append("%s: signals.%s must be a non-empty array"
                                % (tag, k))
            ex = sig.get("exclude_phrases")
            if isinstance(ex, list) and len(set(ex)) != len(ex):
                errs.append("%s: signals.exclude_phrases has duplicates" % tag)
        for k, minitems in (("rewrite_strategy", 1), ("exceptions", 1),
                            ("tags", 1), ("bad_examples", 2),
                            ("good_examples", 2)):
            v = p.get(k)
            if not isinstance(v, list) or len(v) < minitems:
                errs.append("%s: %s needs at least %d item(s)"
                            % (tag, k, minitems))
        for b in p.get("bad_examples") or []:
            if not isinstance(b, dict) or "text" not in b:
                errs.append("%s: bad_examples item missing 'text'" % tag)
            elif set(b) - {"text", "context", "reason"}:
                errs.append("%s: bad_examples item has unexpected keys %s"
                            % (tag, sorted(set(b) - {"text", "context", "reason"})))
        for g in p.get("good_examples") or []:
            if not isinstance(g, dict) or "mode" not in g or "text" not in g:
                errs.append("%s: good_examples item missing 'mode'/'text'" % tag)
            else:
                if g["mode"] not in GOOD_MODES:
                    errs.append("%s: good_examples mode '%s' invalid"
                                % (tag, g["mode"]))
                extra = set(g) - {"mode", "text", "context", "reason"}
                if extra:
                    errs.append("%s: good_examples item has unexpected keys %s"
                                % (tag, sorted(extra)))
        tags = p.get("tags") or []
        if isinstance(tags, list):
            if len(set(tags)) != len(tags):
                errs.append("%s: tags contains duplicates" % tag)
            for t in tags:
                if not KEBAB_RE.match(str(t)):
                    errs.append("%s: tag '%s' is not kebab-case ascii" % (tag, t))
        if "min_occurrences" in p and (not isinstance(p["min_occurrences"], int)
                                       or p["min_occurrences"] < 1):
            errs.append("%s: min_occurrences must be an integer >= 1" % tag)
        if "case_sensitive" in p and not isinstance(p["case_sensitive"], bool):
            errs.append("%s: case_sensitive must be a boolean" % tag)
        for rx in (p.get("signals") or {}).get("regex", []) or []:
            try:
                re.compile(rx)
            except re.error as exc:
                errs.append("%s: regex %r does not compile (%s)" % (tag, rx, exc))
    return errs


def main():
    for path in (YML, SCHEMA):
        if not os.path.exists(path):
            print("FAIL: missing %s" % path, file=sys.stderr)
            return 1
    with open(YML, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    with open(SCHEMA, encoding="utf-8") as fh:
        schema = json.load(fh)

    errors = []
    backend = "explicit"
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema is not None:
        backend = "jsonschema"
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            errors.append("%s: %s" % ("/".join(str(x) for x in err.path) or "<root>",
                                      err.message))
    errors.extend(explicit_check(doc))

    if errors:
        print("FAIL: %d validation error(s) in %s [%s]"
              % (len(errors), YML, backend), file=sys.stderr)
        for e in errors:
            print("  - %s" % e, file=sys.stderr)
        return 1

    patterns = doc["patterns"]
    cats = {}
    for p in patterns:
        cats[p["category"]] = cats.get(p["category"], 0) + 1
    summary = ", ".join("%s=%d" % (k, cats[k]) for k in sorted(cats))
    print("OK: %d patterns valid (schema_version %s, backend %s) [%s]"
          % (len(patterns), doc["schema_version"], backend, summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
