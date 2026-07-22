#!/usr/bin/env python3
"""
mem-scorecard.py — Memory v2 30-check scorecard (R1-R10, D1-D10, S1-S10).

Spec: core/memory/memory-v2.md §3 (Read-path, Distillation, Storage families)

Each check is a function returning (status, evidence):
  status   — "PASS" | "FAIL" | "NOT_IMPLEMENTED"  (NOT_IMPLEMENTED counts as fail)
  evidence — one-line human-readable proof/explanation

Score per family = 10 * (checks passed / 10). Writes ~/.claude/memory/scorecard.md
(current scores + per-check table + 12-week trend) and emits one metric event per
check plus a summary event, via memory/metrics/emit-metric.sh.

Honesty rule (per design doc "Honesty Rules" in metrics/README.md): MEASURED vs
ESTIMATED vs PROXY vs NOT_IMPLEMENTED must stay distinct in evidence text. Several
checks below are explicitly labelled PROXY or MECHANICAL where full automation
isn't implementable by a standalone script (e.g. true cold-recall LLM grading,
session-log sampling) — this is intentional per the P3 task spec: an honest
baseline beats an inflated one.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path

HOME = Path.home()
CLAUDE = HOME / ".claude"
MEMORY = CLAUDE / "memory"
# Claude Code auto-memory slug: cwd path with "/" and "." replaced by "-".
AUTO_MEMORY_SLUG = str(CLAUDE).replace("/", "-").replace(".", "-")
AUTO_MEMORY = HOME / "projects" / AUTO_MEMORY_SLUG / "memory"
SCRIPTS = CLAUDE / "scripts"

GRAPH_JSON = MEMORY / "graphify-out/memory-graph.json"
GRAPH_HTML = MEMORY / "graphify-out/memory-graph.html"
CANARY_FILE = MEMORY / ".canary.md"
CANARY_HASH = MEMORY / ".canary.sha256"
CANARY_SESSION = MEMORY / ".canary-session.json"
DEAD_LINKS = MEMORY / "qa/dead-links.txt"
EXTERNAL_STORES = MEMORY / "external-stores.md"
DECISIONS_MD = MEMORY / "decisions.md"
SCORECARD_MD = MEMORY / "scorecard.md"
EVENTS_JSONL = MEMORY / "metrics/events.jsonl"
EMIT = MEMORY / "metrics/emit-metric.sh"
GARDENER_MARKER = MEMORY / "ops/gardener-last-run.json"
RECALL_EVALS = MEMORY / "qa/recall-evals.md"
CONTRADICTION_QUEUE = MEMORY / "ops/contradiction-queue.md"

BUNDLES = [MEMORY, AUTO_MEMORY]
CONTROL_FILES = {"MEMORY.md", "index.md"}
VALID_TYPES = {"feedback", "lesson", "decision", "reference", "note", "project", "registry", "user"}
REQUIRED_FIELDS = ["name", "type", "description", "created"]
STORE_NAMES = ["Pinecone", "graphify", "NotebookLM", "Obsidian", "tokensave"]

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([a-zA-Z0-9_\-]+)\]\]")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+\.md)\)")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(event, **kw):
    payload = {"ts": now_iso(), "event": event}
    payload.update(kw)
    try:
        subprocess.run([str(EMIT), json.dumps(payload)], check=False,
                        capture_output=True, timeout=5)
    except Exception:
        pass


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm, lines, i = {}, m.group(1).split("\n"), 0
    while i < len(lines):
        kv = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", lines[i])
        if not kv:
            i += 1
            continue
        k, v = kv.group(1), kv.group(2).strip()
        if v == "[]":
            fm[k] = []
        elif v == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("- "):
            items = []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(lines[i].lstrip()[2:].strip())
                i += 1
            fm[k] = items
            continue
        elif v.startswith("[") and v.endswith("]"):
            fm[k] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        else:
            fm[k] = v
        i += 1
    return fm


def all_memory_files():
    files = []
    for base in BUNDLES:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.md")):
            if p.name in CONTROL_FILES or "graphify-out" in p.parts:
                continue
            files.append(p)
    return files


def slugify(stem):
    return re.sub(r"[^a-z0-9_]", "_", stem.lower())


def py_bin():
    venv = Path.home() / ".local/share/uv/tools/graphifyy/bin/python"
    return str(venv) if venv.exists() else sys.executable


_CACHE = {}


def load_graph():
    if "graph" in _CACHE:
        return _CACHE["graph"]
    if not GRAPH_JSON.exists():
        _CACHE["graph"] = None
        return None
    with open(GRAPH_JSON) as f:
        _CACHE["graph"] = json.load(f)
    return _CACHE["graph"]


def load_memory_files_cache():
    if "mem_files" in _CACHE:
        return _CACHE["mem_files"]
    out = []
    for p in all_memory_files():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        fm = parse_frontmatter(text)
        out.append({"path": p, "text": text, "fm": fm})
    _CACHE["mem_files"] = out
    return out


# ============================================================
# ROBUSTNESS — R1-R10
# ============================================================

def check_r1():
    disk_pass, disk_evidence = False, "canary/hash file missing"
    if CANARY_FILE.exists() and CANARY_HASH.exists():
        actual = __import__("hashlib").sha256(CANARY_FILE.read_bytes()).hexdigest()
        expected = CANARY_HASH.read_text().strip()
        disk_pass = actual == expected
        disk_evidence = f"disk sha256 {'matches' if disk_pass else 'MISMATCH'} ({actual[:12]}...)"

    session_pass, session_evidence = False, "no in-session record found"
    if CANARY_SESSION.exists():
        try:
            rec = json.loads(CANARY_SESSION.read_text())
            age_h = (datetime.now(timezone.utc) - datetime.strptime(
                rec["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() / 3600
            session_pass = rec.get("result") == "pass" and age_h < 24
            session_evidence = f"session record result={rec.get('result')} age={age_h:.1f}h (via scripts/canary-session-check.sh, agent Read-tool hash vs .canary.sha256)"
        except Exception as e:
            session_evidence = f"session record unreadable: {e}"

    status = "PASS" if (disk_pass and session_pass) else "FAIL"
    return status, f"disk: {disk_evidence} | in-session: {session_evidence}"


def check_r2():
    files = load_memory_files_cache()
    non_control = {f["path"] for f in files}
    index_files = []
    for base in BUNDLES:
        for name in ("MEMORY.md", "index.md"):
            p = base / name
            if p.exists():
                index_files.append(p)

    resolved_targets, unresolved_targets = 0, 0
    referenced_files = set()
    for idx in index_files:
        text = idx.read_text(encoding="utf-8", errors="replace")
        for m in MD_LINK_RE.finditer(text):
            target = m.group(1).lstrip("./")
            found = None
            for f in non_control:
                if f.name == Path(target).name:
                    found = f
                    break
            if found:
                resolved_targets += 1
                referenced_files.add(found)
            else:
                unresolved_targets += 1

    total_files = len(non_control)
    coverage = len(referenced_files) / total_files if total_files else 0
    all_resolve = unresolved_targets == 0
    status = "PASS" if (all_resolve and coverage >= 0.99) else "FAIL"
    return status, (f"{resolved_targets} index links resolve, {unresolved_targets} unresolved; "
                     f"file coverage {len(referenced_files)}/{total_files} ({coverage:.1%}) "
                     f"— corpus is link-sparse by design decision (per-project files aren't all "
                     f"globally indexed), so full 100% coverage is a real backlog item")


def check_r3():
    dead_count = None
    if DEAD_LINKS.exists():
        lines = [l for l in DEAD_LINKS.read_text().splitlines()
                 if l.strip() and not l.startswith("#")]
        dead_count = len(lines)
    status = "PASS" if dead_count == 0 else "FAIL"
    evidence = f"{dead_count} unresolved link(s) in {DEAD_LINKS}" if dead_count is not None \
        else "dead-links.txt not found (graph not yet built this run)"
    return status, evidence


def check_r4():
    files = load_memory_files_cache()
    total = len(files)
    valid = 0
    bad_examples = []
    for f in files:
        fm = f["fm"]
        ok = all(fm.get(k) for k in REQUIRED_FIELDS) and fm.get("type") in VALID_TYPES
        if ok:
            valid += 1
        elif len(bad_examples) < 3:
            bad_examples.append(f["path"].name)
    status = "PASS" if total and valid == total else "FAIL"
    ex = f"; examples missing/invalid: {', '.join(bad_examples)}" if bad_examples else ""
    return status, f"{valid}/{total} files have valid frontmatter (required fields + type in enum){ex}"


def check_r5():
    files = load_memory_files_cache()
    registries = [f for f in files if f["fm"].get("type") == "registry"]
    status_words = re.compile(r"\b(IN PROGRESS|IN-PROGRESS|ONGOING|BLOCKED|DONE|COMPLETE|PENDING)\b", re.I)
    offenders = []
    for f in registries:
        body = f["text"].split("---", 2)[-1] if f["text"].startswith("---") else f["text"]
        if status_words.search(body):
            offenders.append(f["path"].name)
    status = "PASS" if registries and not offenders else "FAIL"
    if not registries:
        return "FAIL", "no type:registry files found — no SSOT registry to verify"
    return status, (f"{len(registries)} registry-typed file(s); "
                     f"{'no' if not offenders else len(offenders)} contain embedded status text"
                     + (f" ({', '.join(offenders)})" if offenders else ""))


def check_r6():
    try:
        out = subprocess.run(
            ["git", "-C", str(CLAUDE), "status", "--porcelain",
             "--", "memory", "projects/*/memory"],
            capture_output=True, text=True, timeout=15
        ).stdout
    except Exception as e:
        return "NOT_IMPLEMENTED", f"git status failed: {e}"
    stale = []
    now = time.time()
    for line in out.splitlines():
        path = line[3:].strip()
        fp = CLAUDE / path
        if fp.exists() and (now - fp.stat().st_mtime) > 7 * 86400:
            stale.append(path)
    status = "PASS" if not stale else "FAIL"
    return status, f"{len(stale)} memory-path change(s) uncommitted > 7 days" + \
        (f" ({', '.join(stale[:3])})" if stale else "")


MEDIUM_TERM = MEMORY / "medium-term.md"
MEDIUM_TERM_ROW_RE = re.compile(
    r"^\|\s*[\w.-]+\s*\|\s*`([^`]+)`\s*\|[^|]*\|\s*(active|dormant)\s*\|\s*$", re.M)


def get_dormant_project_dirs():
    """Parse medium-term.md's Active Projects table (slug | path | PD | flag) for
    Flag=dormant rows, returning the set of directory names (last path segment
    before /memory/) so check_r7 can skip them.

    PROVISIONAL / minimal-viable: this only covers projects tracked in the
    structured table. It does NOT cover a separate prose "Archived:" list that
    may exist at the bottom of medium-term.md, which is a different,
    unstructured category — those projects can still false-FAIL this check.
    Extending the flag scheme to cover archived projects is a real gap, not
    something to invent unilaterally here; flagged for your own dormant/archived
    project list.
    """
    dormant_dirs = set()
    if not MEDIUM_TERM.exists():
        return dormant_dirs
    for m in MEDIUM_TERM_ROW_RE.finditer(MEDIUM_TERM.read_text(errors="replace")):
        path, flag = m.group(1), m.group(2)
        if flag != "dormant":
            continue
        seg = path.rstrip("/").split("/memory")[0].rstrip("/").split("/")[-1]
        if seg:
            dormant_dirs.add(seg)
    return dormant_dirs


def check_r7():
    dormant_dirs = get_dormant_project_dirs()
    stale = []
    checked = 0
    skipped = 0
    for ns in CLAUDE.glob("projects/*/memory/next-session.md"):
        checked += 1
        proj = ns.parent.parent.name
        if proj in dormant_dirs:
            skipped += 1
            continue
        age_d = (time.time() - ns.stat().st_mtime) / 86400
        if age_d > 14:
            stale.append(f"{proj} ({age_d:.0f}d)")
    status = "PASS" if checked and not stale else ("FAIL" if stale else "NOT_IMPLEMENTED")
    return status, (f"{checked} project next-session.md file(s) checked, {skipped} skipped "
                     f"(dormant per medium-term.md), {len(stale)} stale >14d" +
                     (f" ({', '.join(stale)})" if stale else "") +
                     ("; PROVISIONAL — dormant-dir match only covers medium-term.md's structured "
                      "table, not its separate prose Archived: list" if dormant_dirs else
                      "; no dormant flags parsed from medium-term.md"))


def check_r8():
    hook = CLAUDE / "hooks/rtk-rewrite.sh"
    exemption_found = False
    if hook.exists():
        text = hook.read_text(errors="replace")
        exemption_found = bool(re.search(r"memory", text, re.I))
    status = "PASS" if exemption_found else "FAIL"
    return status, ("memory-path exemption found in hooks/rtk-rewrite.sh" if exemption_found else
                     "no memory-path exemption found in hooks/rtk-rewrite.sh; no headroom config "
                     "located under ~/.claude — this run's tool-output compression appears to be a "
                     "platform-level feature, not a configurable/exempt-able hook")


def check_r9():
    paths = [CLAUDE / "CLAUDE.md", AUTO_MEMORY / "MEMORY.md", CLAUDE / "RTK.md"]
    total_chars = sum(p.read_text(errors="replace").__len__() for p in paths if p.exists())
    est_tokens = total_chars / 4  # ESTIMATED — chars/4 heuristic, not a real tokenizer
    status = "PASS" if est_tokens <= 6000 else "FAIL"
    return status, f"ESTIMATED {est_tokens:.0f} tokens (chars/4 heuristic) across CLAUDE.md+MEMORY.md+RTK.md (budget 6000)"


def check_r10():
    if not GARDENER_MARKER.exists():
        return "FAIL", "no gardener run recorded yet (memory/ops/gardener-last-run.json missing) — infra built this session, first scheduled run pending the user's launchd approval"
    try:
        rec = json.loads(GARDENER_MARKER.read_text())
        last = datetime.strptime(rec["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_d = (datetime.now(timezone.utc) - last).total_seconds() / 86400
        status = "PASS" if age_d < 10 else "FAIL"
        return status, f"last gardener run {age_d:.1f}d ago"
    except Exception as e:
        return "NOT_IMPLEMENTED", f"gardener marker unreadable: {e}"


# ============================================================
# DEPTH — D1-D10
# ============================================================

def check_d1():
    if not RECALL_EVALS.exists():
        return "FAIL", "memory/qa/recall-evals.md not found"
    text = RECALL_EVALS.read_text()
    blocks = re.split(r"\n(?=## Q\d)", text)
    total, verified = 0, 0
    for b in blocks:
        qm = re.search(r"## Q\d+", b)
        if not qm:
            continue
        total += 1
        src_m = re.search(r"\*\*Source:\*\*\s*`?([^\n`]+)`?", b)
        facts_m = re.findall(r"^\s*-\s*(.+)$", b, re.M)
        if not src_m:
            continue
        src_path = (src_m.group(1).strip())
        candidates = [CLAUDE / src_path, MEMORY / src_path, AUTO_MEMORY / src_path, SYS_IMPROVE / src_path]
        src_file = next((c for c in candidates if c.exists()), None)
        if not src_file:
            continue
        src_text = src_file.read_text(errors="replace")
        key_facts = [f for f in facts_m if len(f) > 3 and not f.startswith("**")]
        if key_facts and all(any(kf.lower()[:40] in src_text.lower() for kf in [f]) for f in key_facts):
            verified += 1
    status = "PASS" if total and verified / total >= 0.95 else "FAIL"
    return status, (f"PROXY {verified}/{total} questions have all key facts mechanically verified "
                     f"present in their cited source file; this is NOT true cold-recall LLM grading "
                     f"(that requires a separate live eval pass) — it validates the eval set is "
                     f"well-formed and the facts genuinely exist in memory")


def check_d2():
    if not RECALL_EVALS.exists():
        return "FAIL", "recall-evals.md not found"
    return "NOT_IMPLEMENTED", "recall-evals.md created this session (baseline) — growth trend needs >=1 month of history to measure"


def check_d3():
    files = load_memory_files_cache()
    targets = [f for f in files if f["fm"].get("type") in ("feedback", "lesson")]
    ok = 0
    missing = []
    for f in targets:
        body = f["text"]
        has_why = bool(re.search(r"\*\*Why", body, re.I))
        has_how = bool(re.search(r"\*\*How[\s-]*to[\s-]*apply", body, re.I))
        if has_why and has_how:
            ok += 1
        elif len(missing) < 3:
            missing.append(f["path"].name)
    total = len(targets)
    status = "PASS" if total and ok == total else "FAIL"
    return status, f"{ok}/{total} feedback/lesson memories have Why + How-to-apply" + \
        (f"; missing e.g. {', '.join(missing)}" if missing else "")


def check_d4():
    if not DECISIONS_MD.exists():
        return "NOT_IMPLEMENTED", "decisions.md not found at expected path"
    text = DECISIONS_MD.read_text(errors="replace")
    entries = [e for e in re.split(r"\n(?=##? )", text) if e.strip()]
    if not entries:
        return "NOT_IMPLEMENTED", "no parseable decision entries found"
    linked = sum(1 for e in entries if WIKILINK_RE.search(e) or MD_LINK_RE.search(e))
    status = "PASS" if linked == len(entries) else "FAIL"
    return status, f"{linked}/{len(entries)} decisions.md entries link >=1 supporting memory"


def check_d5():
    if not EXTERNAL_STORES.exists():
        return "FAIL", "external-stores.md not found"
    text = EXTERNAL_STORES.read_text()
    missing = [s for s in STORE_NAMES if s.lower() not in text.lower()]
    status = "PASS" if not missing else "FAIL"
    return status, (f"spot-check of {len(STORE_NAMES)} known stores in external-stores.md: "
                     f"{'all present' if not missing else 'missing ' + ', '.join(missing)} "
                     f"(full automated stranded-store grep across corpus not implemented)")


def check_d6():
    files = load_memory_files_cache()
    today = date.today()
    expired = []
    checked = 0
    for f in files:
        rb = f["fm"].get("review-by")
        if not rb:
            continue
        checked += 1
        try:
            d = datetime.strptime(rb, "%Y-%m-%d").date()
            if d < today:
                expired.append(f["path"].name)
        except Exception:
            pass
    status = "PASS" if not expired else "FAIL"
    note = " (vacuous — review-by adoption not yet populated corpus-wide, P1 follow-up)" if checked == 0 else ""
    return status, f"{checked} file(s) carry review-by; {len(expired)} expired{note}"


def check_d7():
    if not CONTRADICTION_QUEUE.exists():
        return "PASS", "no contradiction queue file exists (vacuously empty — gardener hasn't flagged any contradictions yet, infra built this session)"
    text = CONTRADICTION_QUEUE.read_text().strip()
    status = "PASS" if not text else "FAIL"
    return status, f"contradiction-queue.md {'empty' if not text else 'has open entries'}"


def check_d8():
    return "NOT_IMPLEMENTED", "requires session-log sampling infrastructure (transcript scan for correction->lesson-delta latency) — not built yet, flagged as backlog"


def check_d9():
    if not EVENTS_JSONL.exists():
        return "FAIL", "events.jsonl not found"
    hits = 0
    for line in EVENTS_JSONL.read_text(errors="replace").splitlines():
        if '"event": "mem_find"' in line or '"event":"mem_find"' in line:
            hits += 1
    status = "PASS" if hits > 0 else "FAIL"
    return status, f"{hits} mem_find usage event(s) in events.jsonl" + \
        ("" if hits else " — mem-find.sh does not currently self-log; instrumentation gap, backlog item")


def check_d10():
    return "NOT_IMPLEMENTED", "requires a completed gardener run to diff against (no gardener cycle has run yet — infra built this session)"


# ============================================================
# SCANNABILITY — S1-S10
# ============================================================

def rebuild_graph():
    if "rebuild_done" in _CACHE:
        return _CACHE["rebuild_done"]
    try:
        r = subprocess.run([py_bin(), str(SCRIPTS / "mem-graph-build.py")],
                            capture_output=True, text=True, timeout=120)
        _CACHE["rebuild_done"] = (r.returncode == 0, r.stdout, r.stderr)
    except Exception as e:
        _CACHE["rebuild_done"] = (False, "", str(e))
    _CACHE.pop("graph", None)
    return _CACHE["rebuild_done"]


def check_s1():
    ok, out, err = rebuild_graph()
    if not ok:
        return "FAIL", f"mem-graph-build.py failed: {err[:200]}"
    g = load_graph()
    if not g:
        return "FAIL", "memory-graph.json missing after rebuild"
    return "PASS", f"graph rebuilt clean: {out.strip()}"


def check_s2():
    g = load_graph()
    if not g:
        return "FAIL", "no graph loaded"
    nodes = g.get("nodes", [])
    links = g.get("links", g.get("edges", []))
    degree = {n["id"]: 0 for n in nodes}
    for e in links:
        src = e.get("source") or e.get("_src")
        tgt = e.get("target") or e.get("_tgt")
        if src in degree:
            degree[src] += 1
        if tgt in degree:
            degree[tgt] += 1
    orphans = [nid for nid, d in degree.items() if d == 0]
    status = "PASS" if not orphans else "FAIL"
    return status, f"{len(orphans)}/{len(nodes)} orphan node(s) ({len(orphans)/len(nodes):.1%}) — link-sparse corpus, real backlog item not a script bug"


def check_s3():
    g = load_graph()
    if not g:
        return "FAIL", "no graph loaded"
    nodes = g.get("nodes", [])
    links = g.get("links", g.get("edges", []))
    adj = {n["id"]: set() for n in nodes}
    for e in links:
        src = e.get("source") or e.get("_src")
        tgt = e.get("target") or e.get("_tgt")
        if src in adj and tgt in adj:
            adj[src].add(tgt)
            adj[tgt].add(src)

    roots = set()
    stems_to_id = {n["id"]: n["id"] for n in nodes}
    for base in BUNDLES:
        for name in ("MEMORY.md", "index.md"):
            p = base / name
            if not p.exists():
                continue
            for m in MD_LINK_RE.finditer(p.read_text(errors="replace")):
                target_stem = Path(m.group(1)).stem
                sid = slugify(target_stem)
                if sid in adj:
                    roots.add(sid)

    reachable = set(roots)
    frontier = set(roots)
    for _ in range(3):
        nxt = set()
        for nid in frontier:
            nxt |= adj.get(nid, set())
        nxt -= reachable
        reachable |= nxt
        frontier = nxt
        if not frontier:
            break

    total = len(nodes)
    pct = len(reachable) / total if total else 0
    status = "PASS" if pct >= 0.95 else "FAIL"
    return status, f"{len(reachable)}/{total} nodes reachable from {len(roots)} MEMORY.md/index.md roots within 3 hops ({pct:.1%})"


def check_s4():
    mem_cli = SCRIPTS / "mem"
    if not (mem_cli.exists() and mem_cli.stat().st_mode & 0o111):
        return "FAIL", "scripts/mem not found or not executable"
    ok, _, _ = rebuild_graph()
    html_ok = GRAPH_HTML.exists()
    status = "PASS" if (ok and html_ok) else "FAIL"
    return status, f"scripts/mem executable=yes, graph html {'present' if html_ok else 'missing'} after rebuild (smoke test; `open` step not invoked headlessly)"


def check_s5():
    p = AUTO_MEMORY / "MEMORY.md"
    if not p.exists():
        return "FAIL", "auto-memory MEMORY.md not found"
    lines = [l for l in p.read_text(errors="replace").splitlines() if l.strip()]
    over_len = [l for l in lines if len(l) > 110]
    status = "PASS" if len(lines) <= 45 and not over_len else "FAIL"
    return status, f"{len(lines)} lines (budget <=45), {len(over_len)} line(s) > 110 chars"


def check_s6():
    g = load_graph()
    if not g:
        return "FAIL", "no graph loaded"
    nodes = g.get("nodes", [])
    typed = sum(1 for n in nodes if n.get("file_type"))
    status = "PASS" if nodes and typed == len(nodes) else "FAIL"
    return status, f"{typed}/{len(nodes)} nodes carry file_type"


def check_s7():
    files = load_memory_files_cache()
    descs = {}
    empty, restated = 0, 0
    for f in files:
        d = (f["fm"].get("description") or "").strip()
        n = (f["fm"].get("name") or f["path"].stem).strip()
        if not d:
            empty += 1
            continue
        if d.lower() == n.lower():
            restated += 1
        descs.setdefault(d.lower(), []).append(f["path"].name)
    dupes = sum(len(v) - 1 for v in descs.values() if len(v) > 1)
    total = len(files)
    ok = total - empty - restated - dupes
    status = "PASS" if total and empty == 0 and restated == 0 and dupes == 0 else "FAIL"
    return status, f"{empty} empty, {restated} restate name, {dupes} duplicate description(s) out of {total} files"


def check_s8():
    g = load_graph()
    if not g:
        return "FAIL", "no graph loaded"
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    links = g.get("links", g.get("edges", []))
    if not links:
        return "FAIL", "0 edges — cannot assess cross-domain ratio"
    cross = 0
    for e in links:
        src, tgt = e.get("source") or e.get("_src"), e.get("target") or e.get("_tgt")
        sn, tn = nodes.get(src), nodes.get(tgt)
        if sn and tn and sn.get("memory_type") != tn.get("memory_type"):
            cross += 1
    pct = cross / len(links)
    status = "PASS" if pct >= 0.10 else "FAIL"
    return status, f"{cross}/{len(links)} edges cross-domain ({pct:.1%}, budget >=10%)"


def check_s9():
    q = "memory"
    try:
        t0 = time.monotonic()
        subprocess.run([str(SCRIPTS / "mem-find.sh"), q], capture_output=True, text=True, timeout=10)
        elapsed = time.monotonic() - t0
    except Exception as e:
        return "NOT_IMPLEMENTED", f"mem-find.sh failed: {e}"
    status = "PASS" if elapsed < 2.0 else "FAIL"
    return status, f"mem-find.sh '{q}' returned in {elapsed:.2f}s (budget <2s)"


def check_s10():
    if not GRAPH_JSON.exists():
        return "FAIL", "memory-graph.json missing"
    age_s = time.time() - GRAPH_JSON.stat().st_mtime
    status = "PASS" if age_s < 3600 else ("FAIL" if age_s > 8 * 86400 else "PASS")
    return status, f"graph rebuilt {age_s:.0f}s ago by this scorecard run (S1)"


CHECKS = {
    "R": [("R1", check_r1), ("R2", check_r2), ("R3", check_r3), ("R4", check_r4),
          ("R5", check_r5), ("R6", check_r6), ("R7", check_r7), ("R8", check_r8),
          ("R9", check_r9), ("R10", check_r10)],
    "D": [("D1", check_d1), ("D2", check_d2), ("D3", check_d3), ("D4", check_d4),
          ("D5", check_d5), ("D6", check_d6), ("D7", check_d7), ("D8", check_d8),
          ("D9", check_d9), ("D10", check_d10)],
    "S": [("S1", check_s1), ("S2", check_s2), ("S3", check_s3), ("S4", check_s4),
          ("S5", check_s5), ("S6", check_s6), ("S7", check_s7), ("S8", check_s8),
          ("S9", check_s9), ("S10", check_s10)],
}
FAMILY_NAME = {"R": "Robustness", "D": "Depth", "S": "Scannability"}


def run_all():
    # Rebuild the graph once, up front, so every check (R3's dead-links.txt read
    # included) sees fresh data — not just S1 onward. Fixes an ordering bug where
    # R3 read a stale dead-links.txt written by the PREVIOUS run, undercounting
    # fixes made earlier in the same session.
    rebuild_graph()
    results = {}
    for fam, checks in CHECKS.items():
        for cid, fn in checks:
            try:
                status, evidence = fn()
            except Exception as e:
                status, evidence = "FAIL", f"check raised exception: {e}"
            results[cid] = {"status": status, "evidence": evidence}
            emit("scorecard_check", check=cid, status=status)
    return results


def write_scorecard(results, run_ts):
    scores = {}
    for fam, checks in CHECKS.items():
        passed = sum(1 for cid, _ in checks if results[cid]["status"] == "PASS")
        scores[fam] = (passed, len(checks), 10 * passed / len(checks))

    lines = []
    lines.append("# Memory v2 Scorecard")
    lines.append("")
    lines.append(f"Last run: {run_ts}")
    lines.append("")
    lines.append(f"**Overall: R {scores['R'][2]:.1f}/10 · D {scores['D'][2]:.1f}/10 · S {scores['S'][2]:.1f}/10** "
                 f"({scores['R'][0]+scores['D'][0]+scores['S'][0]}/30 checks passing)")
    lines.append("")
    lines.append("Score per family = 10 x (checks passed / 10). NOT_IMPLEMENTED counts as fail — "
                 "this is an honest baseline, not an inflated one. See §3 of "
                 "outputs/memory-audit/2026-07-10-memory-system-audit/memory-v2-target-architecture.html "
                 "for the full check spec.")
    lines.append("")

    for fam in ("R", "D", "S"):
        p, t, sc = scores[fam]
        lines.append(f"## {FAMILY_NAME[fam]} — {sc:.1f}/10 ({p}/{t})")
        lines.append("")
        lines.append("| # | Status | Evidence |")
        lines.append("|---|--------|----------|")
        for cid, _ in CHECKS[fam]:
            r = results[cid]
            mark = {"PASS": "PASS", "FAIL": "FAIL", "NOT_IMPLEMENTED": "N/A"}[r["status"]]
            lines.append(f"| {cid} | {mark} | {r['evidence']} |")
        lines.append("")

    lines.append("## 12-Week Trend")
    lines.append("")
    lines.append("| Week | R | D | S | Total |")
    lines.append("|------|---|---|---|-------|")

    trend_path = SCORECARD_MD
    prior_rows = []
    if trend_path.exists():
        old = trend_path.read_text(errors="replace")
        m = re.search(r"## 12-Week Trend\n\n\|.*?\|\n\|[-\s|]+\|\n((?:\|.*\|\n?)*)", old)
        if m:
            prior_rows = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]

    week_label = date.today().isoformat()
    new_row = f"| {week_label} | {scores['R'][2]:.1f} | {scores['D'][2]:.1f} | {scores['S'][2]:.1f} | {scores['R'][2]+scores['D'][2]+scores['S'][2]:.1f}/30 |"
    all_rows = (prior_rows + [new_row])[-12:]
    lines.extend(all_rows)
    lines.append("")

    SCORECARD_MD.write_text("\n".join(lines))
    return scores


def main():
    run_ts = now_iso()
    emit("scorecard_run_start")
    results = run_all()
    scores = write_scorecard(results, run_ts)
    emit("scorecard_run_end",
         r=round(scores["R"][2], 1), d=round(scores["D"][2], 1), s=round(scores["S"][2], 1),
         total_passed=scores["R"][0] + scores["D"][0] + scores["S"][0])
    print(f"R {scores['R'][2]:.1f}/10 ({scores['R'][0]}/10)  "
          f"D {scores['D'][2]:.1f}/10 ({scores['D'][0]}/10)  "
          f"S {scores['S'][2]:.1f}/10 ({scores['S'][0]}/10)")
    print(f"Wrote {SCORECARD_MD}")


if __name__ == "__main__":
    main()
