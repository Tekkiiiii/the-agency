#!/usr/bin/env python3
"""mem-dupe-scan.py — near-duplicate candidate detector for the memory estate.

Closes the "no near-duplicate detector exists" gap named in
memory/gardener-runbook.md §Known gaps. This is the MECHANICAL half of the
Gardener's Curate step (step 2): it produces evidence-ranked candidate PAIRS.
It deliberately does NOT decide anything — adjudicating whether a pair is a
true duplicate, a legitimate specialisation, or a contradiction needs LLM
judgment, and every destructive outcome (merge/archive/delete) goes to
memory/ops/approval-queue.md for the operator, never auto-applied.

Method: TF-IDF over the body text (frontmatter stripped) with pure-stdlib
cosine similarity — no numpy/sklearn dependency, so it runs under the same
interpreter as the rest of the gardener pipeline on any machine.

Scope boundary is imported from memory_scope.py — the same EXCLUDE_NAMES /
EXCLUDE_DIRS every other memory script uses. Do not redefine it here; that
divergence is exactly the 2026-07-27 R4 scan-scope bug.

Usage:
    python3 scripts/mem-dupe-scan.py                 # both default corpora
    python3 scripts/mem-dupe-scan.py --threshold 0.4
    python3 scripts/mem-dupe-scan.py --json out.json
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_scope import is_excluded  # noqa: E402

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


DEFAULT_DIRS = [Path(agency_root(str(Path.home()))) / "memory"]

# Stopwords: English function words plus corpus-wide boilerplate that would
# otherwise make every memory file look similar to every other one.
STOP = set("""
a an the and or but if then than that this these those of in on at to for from by with
is are was were be been being do does did doing have has had having it its as not no
you your we our they their he she i me my mine so such can could should would will
when where which who whom what how why all any both each few more most other some own
same too very s t just don now use used using via per see also into out up down over
under again further once here there why how because while about against between
name type description created links review by md file files memory claude
""".split())

TOKEN_RE = re.compile(r"[a-z][a-z0-9_-]{2,}")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def read_description(text: str) -> str:
    m = re.search(r"^description:\s*(.+)$", text[:2000], re.M)
    return m.group(1).strip() if m else ""


def tokenize(text: str):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


def collect(dirs):
    docs = []
    for root in dirs:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            if is_excluded(p, root):
                continue
            try:
                raw = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            body = strip_frontmatter(raw)
            toks = tokenize(body)
            if len(toks) < 15:          # too thin to judge; report separately
                docs.append({"path": str(p), "tokens": toks, "tf": Counter(toks),
                             "desc": read_description(raw), "words": len(toks),
                             "thin": True})
                continue
            docs.append({"path": str(p), "tokens": toks, "tf": Counter(toks),
                         "desc": read_description(raw), "words": len(toks),
                         "thin": False})
    return docs


def tfidf_vectors(docs):
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(set(d["tf"]))
    vecs = []
    for d in docs:
        v = {}
        maxtf = max(d["tf"].values()) if d["tf"] else 1
        for term, cnt in d["tf"].items():
            idf = math.log((n + 1) / (df[term] + 1)) + 1.0
            v[term] = (0.5 + 0.5 * cnt / maxtf) * idf
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({k: x / norm for k, x in v.items()})
    return vecs


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b[t] for t, w in a.items() if t in b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="append", default=None)
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    dirs = [Path(d).expanduser() for d in args.dir] if args.dir else DEFAULT_DIRS
    docs = collect(dirs)
    vecs = tfidf_vectors(docs)

    pairs = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            s = cosine(vecs[i], vecs[j])
            if s >= args.threshold:
                # Jaccard on the token SETS is a useful second opinion: high
                # cosine + low jaccard usually means "same jargon, different
                # subject", which is the main false-positive mode here.
                si, sj = set(docs[i]["tokens"]), set(docs[j]["tokens"])
                jac = len(si & sj) / max(len(si | sj), 1)
                pairs.append({
                    "cosine": round(s, 3), "jaccard": round(jac, 3),
                    "a": docs[i]["path"], "b": docs[j]["path"],
                    "a_desc": docs[i]["desc"][:180],
                    "b_desc": docs[j]["desc"][:180],
                    "a_words": docs[i]["words"], "b_words": docs[j]["words"],
                    "shared_top": [t for t, _ in Counter(
                        {t: min(docs[i]["tf"][t], docs[j]["tf"][t])
                         for t in si & sj}).most_common(10)],
                })
    pairs.sort(key=lambda p: -p["cosine"])
    out = {"scanned": len(docs), "threshold": args.threshold,
           "pairs_found": len(pairs), "pairs": pairs[:args.top],
           "thin_files": [d["path"] for d in docs if d["thin"]]}

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2))
    print(f"scanned={len(docs)} threshold={args.threshold} pairs>={args.threshold}: {len(pairs)}")
    for p in pairs[:args.top]:
        print(f"{p['cosine']:.3f} jac={p['jaccard']:.3f}  "
              f"{Path(p['a']).name}  <->  {Path(p['b']).name}   "
              f"[{','.join(p['shared_top'][:6])}]")


if __name__ == "__main__":
    main()
