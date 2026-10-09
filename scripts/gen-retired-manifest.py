#!/usr/bin/env python3
"""gen-retired-manifest.py - generate (or check) retired-manifest.json.

The manifest lists every file the repo once shipped under skills/, agents/,
runbooks/ or core/ and no longer ships, with the sha256 of EVERY version that
was ever shipped at that path. cli/lib/retired-prune.js reads it to delete stale
files from an installed agency root on `agency upgrade`, install.sh, install.ps1
and `agency prune`: a file whose hash matches a shipped version is an untouched
leftover (safe to delete); anything else was edited by the user and is archived
or kept; a path that is not in this file is never touched.

  python3 scripts/gen-retired-manifest.py            write retired-manifest.json
  python3 scripts/gen-retired-manifest.py --check    regenerate in memory, exit 1 if the
                                                     committed file differs (CI guard)

Needs the FULL git history (CI: actions/checkout fetch-depth: 0). A path is
RETIRED when it existed in any commit reachable from HEAD under one of the four
trees and does not exist at HEAD. Excluded: paths listed in core/.preserve (now
or in any past version - user data, never ours to delete), OS/cache noise, and any
path whose name contains a personal term from .github/scripts/check-privacy.js (the
repo is public and a path in this file would publish the name; those files were
dropped from the repo for privacy and belong to one operator's own install).

Hash = sha256 of the blob bytes with CRLF -> LF, matching what the prune step
computes for an installed file (so a Windows checkout with autocrlf still matches).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

TREES = ["skills/", "agents/", "runbooks/", "core/"]
MANIFEST = "retired-manifest.json"
NOISE_BASENAMES = {".DS_Store", "Thumbs.db"}
ZERO = "0" * 40  # sha1 repos; sha256 repos use 64 zeros, handled by set(c) == {"0"}


def git(args, repo, input_bytes=None, check=True):
    p = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false"] + args,
                       input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        sys.stderr.write("git %s failed: %s\n" % (" ".join(args), p.stderr.decode("utf-8", "replace")))
        sys.exit(2)
    return p


def private_terms(repo):
    """The C4 personal terms, read from the privacy check so there is one list."""
    try:
        with open(os.path.join(repo, ".github", "scripts", "check-privacy.js"), encoding="utf-8") as f:
            block = re.search(r"const TERMS = \[(.*?)\];", f.read(), re.S)
        return [t.lower() for t in re.findall(r"'([^']+)'", block.group(1))] if block else []
    except OSError:
        return []


def is_noise(path):
    base = path.rsplit("/", 1)[-1]
    return base in NOISE_BASENAMES or base.endswith(".pyc") or "/__pycache__/" in path


def history_pairs(repo):
    """(path, blob_sha) for every non-deleted entry in every commit's diff, merges included."""
    # --full-history + -m: no history simplification, and merge commits are diffed
    # against each parent, so a blob that only a merge introduced is not missed.
    out = git(["log", "--raw", "--no-abbrev", "--no-renames", "--full-history", "-m", "--root",
               "-z", "--format=", "--"] + TREES, repo).stdout
    toks = out.split(b"\0")
    pairs = set()
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.startswith(b":"):
            meta = t[1:].decode("ascii", "replace").split()
            path = toks[i + 1].decode("utf-8", "surrogateescape")
            i += 2
            # meta: oldmode newmode oldsha newsha status
            if len(meta) >= 5:
                newmode, newsha, status = meta[1], meta[3], meta[4]
                if status[0] != "D" and set(newsha) != {"0"} and newmode not in ("120000", "160000"):
                    pairs.add((path, newsha))
        else:
            i += 1
    return pairs


def head_paths(repo):
    out = git(["ls-tree", "-r", "-z", "--name-only", "HEAD", "--"] + TREES, repo).stdout
    return set(p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p)


def blob_hashes(repo, shas):
    """sha256 of each blob with CRLF -> LF, via one `git cat-file --batch`."""
    shas = sorted(shas)
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate("".join(s + "\n" for s in shas).encode("ascii"))
    if proc.returncode != 0:
        sys.stderr.write("git cat-file failed: %s\n" % err.decode("utf-8", "replace"))
        sys.exit(2)
    res = {}
    pos = 0
    for sha in shas:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode("ascii").split()
        if len(header) < 3 or header[1] != "blob":
            sys.stderr.write("unexpected cat-file header for %s: %r\n" % (sha, header))
            sys.exit(2)
        size = int(header[2])
        data = out[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        res[sha] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    return res


def preserved_paths(repo):
    """core/ paths ever listed in core/.preserve, as repo-relative paths."""
    out = git(["log", "--format=", "--raw", "--no-abbrev", "--full-history", "-m", "--root", "-z", "--",
               "core/.preserve"], repo).stdout
    blobs = set()
    toks = out.split(b"\0")
    for i, t in enumerate(toks):
        if t.startswith(b":"):
            meta = t[1:].decode("ascii").split()
            if len(meta) >= 5 and meta[4][0] != "D" and set(meta[3]) != {"0"}:
                blobs.add(meta[3])
    keep = set()
    for sha in sorted(blobs):
        body = git(["cat-file", "blob", sha], repo).stdout.decode("utf-8", "replace")
        for line in body.splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                keep.add("core/" + line)
    return keep


def build(repo):
    shallow = git(["rev-parse", "--is-shallow-repository"], repo).stdout.decode().strip()
    if shallow == "true":
        sys.stderr.write("gen-retired-manifest: needs full history (actions/checkout fetch-depth: 0); "
                         "this clone is shallow.\n")
        sys.exit(2)
    head = git(["rev-parse", "HEAD"], repo).stdout.decode().strip()
    pairs = history_pairs(repo)
    live = head_paths(repo)
    protected = preserved_paths(repo)
    terms = private_terms(repo)
    candidates = {(p, s) for (p, s) in pairs if p not in live and p not in protected and not is_noise(p)}
    wanted = {(p, s) for (p, s) in candidates if not any(t in p.lower() for t in terms)}
    excluded_private = sorted({p for (p, _) in candidates} - {p for (p, _) in wanted})
    hashes = blob_hashes(repo, {s for _, s in wanted})
    paths = {}
    for p, s in wanted:
        paths.setdefault(p, set()).add(hashes[s])
    return {
        "version": 1,
        "generated_from": head,
        "trees": TREES,
        "paths": {p: sorted(paths[p]) for p in sorted(paths)},
    }, excluded_private


def render(m):
    return json.dumps(m, indent=1, sort_keys=False, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed manifest is stale")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    new, excluded = build(repo)
    target = os.path.join(repo, MANIFEST)
    if not a.check:
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(render(new))
        print("wrote %s: %d retired paths from %s (%d excluded: personal term in the path)"
              % (MANIFEST, len(new["paths"]), new["generated_from"][:12], len(excluded)))
        return 0
    try:
        with open(target, encoding="utf-8") as f:
            old = json.load(f)
    except FileNotFoundError:
        print("FAIL %s is missing. Run: python3 scripts/gen-retired-manifest.py" % MANIFEST)
        return 1
    except ValueError as e:
        print("FAIL %s is not valid JSON (%s). Run: python3 scripts/gen-retired-manifest.py" % (MANIFEST, e))
        return 1
    op, np_ = old.get("paths", {}), new["paths"]
    missing = sorted(set(np_) - set(op))      # deleted from the repo, not listed
    extra = sorted(set(op) - set(np_))        # listed, but not a retired path
    changed = sorted(p for p in set(op) & set(np_) if op[p] != np_[p])
    meta_bad = old.get("version") != new["version"] or old.get("trees") != new["trees"]
    if not (missing or extra or changed or meta_bad):
        print("ok   %s is current (%d retired paths, %d excluded: personal term in the path)"
              % (MANIFEST, len(np_), len(excluded)))
        return 0
    for p in missing:
        print("FAIL deleted from the repo but missing from %s: %s" % (MANIFEST, p))
    for p in extra:
        print("FAIL listed in %s but not a retired path (still shipped, or never was): %s" % (MANIFEST, p))
    for p in changed:
        print("FAIL shipped hashes differ for: %s" % p)
    if meta_bad:
        print("FAIL version/trees header differs")
    print("Run: python3 scripts/gen-retired-manifest.py   (then commit %s)" % MANIFEST)
    return 1


if __name__ == "__main__":
    sys.exit(main())
