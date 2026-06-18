---
name: save-state
description: >
  Freezes the current session — reads project state, writes all session-end files,
  resets the turn counter, outputs a single confirmation. Fully autonomous, no user
  interaction. Invoke as /save-state [slug], /save-state (auto-detects from cwd), or
  /save-state all. When to trigger: at the end of every working session before closing; before switching to a different project; when
  mid-flight work needs to be preserved for the next session; after any significant
  milestone or decision; and whenever the user says "save state." Key
  capabilities: spawns a fully autonomous subagent so zero work happens in the calling
  session, reads mid-flight files (src/, lib/, app/, backend/, etc.) to capture what
  was half-done, writes session logs, heartbeat updates, decisions records, next-session
  briefs, and STATE.md summaries. Also syncs root lessons from ~/.claude/memory/
  lessons/ into the project's memory/ dir, and fires a best-effort Pinecone upsert for
  long-term retrieval. Ideal for project directors maintaining multiple active projects
  who need reliable session continuity across context switches. Also useful for post-
  incident reviews, onboarding a colleague into a project, and feeding session data into
  a project memory or RAG system.
---

# Save State

Spawns a subagent that reads project state, scans mid-flight files, writes all session-end
files, and outputs a single confirmation. Caller spawns and waits — zero work done in the
calling session.

## SSOT: medium-term.md

The **primary source of truth** for project locations is `~/.claude/memory/medium-term.md`
— the Active Projects table. Read it FIRST.

## Auto-Detect Project (no-argument invocation)

When invoked as `/save-state` with **NO slug argument**, resolve the project from the
current working directory — never iterate all projects.

1. **Read `medium-term.md`** — the Active Projects table lists `{slug}` and `{path}` per project.
2. **Match cwd against project paths:**
   - If cwd **equals** a project path → use that slug.
   - If cwd **starts with** a project path (subdirectory) → use the parent project slug.
3. **If no path match:** attempt to read `{cwd}/memory/heartbeat.md` or `{cwd}/STATE.md`.
   - If found, treat the cwd root as the project and infer the slug from the directory name.
4. **If nothing resolves:** output and stop:
   ```
   Cannot determine project. Pass a slug explicitly:
   /save-state [project-slug]
   Hint: Check ~/.claude/memory/medium-term.md for the current project list.
   ```
   **Stop. Do not read all medium-term entries. Do not iterate over all projects.**

## Argument Resolution

After auto-detect (or if a slug was provided), resolve the target:

| Argument | Action |
|---|---|
| `all` | Save all active projects in `medium-term.md`, in parallel via spawned subagents |
| `[slug]` | Save exactly one project — run the full ritual on that slug only |
| no arg → cwd resolves | Save that one project — run the full ritual on the resolved slug |
| no arg → cwd fails | Fail with message, stop |

### If `all` — Parallel Multi-Project Save

Read `medium-term.md` Active Projects table. For each project, spawn a save-state
subagent in parallel. Wait for all to complete. Output:

```
save-state done! — {n} projects saved
  {slug1} ✓
  {slug2} ✓
  ...
```

Subagent prompt per project: same as the single-project ritual below, scoped to
`{project}/`. Step 12 (Pinecone upsert) fires per-project after each subagent reports.

## If Slug Not Found

1. Check `~/.claude/memory/medium-term.md` Active Projects table — the SSOT.
2. If not in medium-term.md → output:

   ```
   PROJECT NOT FOUND: {slug}
   Hint: Check ~/.claude/memory/medium-term.md for the current project list.
   ```

   **Stop. Do not fall back to other projects or search broadly.**

## Step 1 — Spawn Subagent

Use the Agent tool to spawn a general-purpose sonnet subagent. The subagent owns the
entire ritual — do not do any reading or writing yourself.

Subagent prompt:

"You own the save-state ritual for {project}. Run it completely.

PERMISSIONS: read-write-create on ALL paths below. No restrictions.

## Scope
- Project root: `{project}/`
- Memory dir: `{project}/memory/` — includes heartbeat.md, decisions.md, next-session.md, sessions/, lessons/
- State tracking: `{project}/.claude/save-state-state.json`
- Lessons root: `~/.claude/memory/lessons/`
- Lessons dir: `{project}/memory/lessons/`
- Task folder: `{project}/memory/tasks/`  # ongoing/, completed/, revisions/ subdirectories
- Active tasks: `{project}/memory/tasks/ongoing/*.md`
- Mid-flight scan dirs: `src/`, `lib/`, `app/`, `backend/`, `frontend/src/`, `components/`, `src-tauri/src/`, `web/src/`, `api/`, `tests/`, `spec/`
- Optional project root files: `{project}/STATE.md`, `{project}/CLAUDE.md`

## Step 0 — Write next-session.md Placeholder (FIRST — before any heavy reads)

**This step runs BEFORE any other step.** Its purpose: ensure that even if the subagent
hangs or dies during the heavy read/write steps, the handoff file is not left stale from
a prior session. A stale next-session.md from a hung prior run causes the PD to re-enter
the same decision loop on the next resume.

Read ONLY: `{project}/memory/next-session.md` (the existing file, to preserve Phase/Blockers).
Then immediately overwrite it with a tombstone placeholder:

```
# {slug}
Phase: [copy existing Phase: line verbatim, or "UNKNOWN if file unreadable"]
Next: SAVE-STATE IN PROGRESS — do not resume until save-state completes and overwrites this file
Blockers: save-state subagent running (tombstone — will be overwritten by Step 6)
Decisions: see decisions.md
Mid-flight: unknown (save-state not yet complete)
Delegated: unknown
Pending inbound: unknown
Last saved: {YYYY-MM-DD} (tombstone — will be overwritten)
```

**This tombstone is intentionally incomplete.** Step 6 will overwrite it with the full content
(after session log and heartbeat are captured, but before the decisions rewrite).
If the subagent dies before Step 6, pd-resume will see the tombstone `Next:` and know NOT to
resume (it will not match any Tekki-blocked pattern but clearly signals "do not trust this file").

After writing the tombstone: proceed immediately to Step 1.

## Step 1 — Read Baseline (Delta-Driven Mode)

**First: check for a session delta.** Read `{project}/memory/agents/pd-scratch.md` and look for
a `## Session Delta` section at the bottom. This section is written by the PD at session end
and contains a compact summary of what changed this session.

**If a valid session delta is found** (timestamp within last 2 hours, status NOT marked INCOMPLETE):

**Delta self-validation gate (run before trusting the delta):**
Before accepting the delta as source of truth, run a cheap reality cross-check to catch
confidently-wrong deltas (stale, truncated, or out-of-sync with actual file state):

1. If the project is a git repo: run `git -C {project} status --short 2>/dev/null` and collect
   modified/untracked file paths (strip the leading status chars). Skip if not a git repo.
2. If not a git repo (or git fails): scan the mid-flight dirs (src/, lib/, app/, backend/,
   frontend/src/, components/, src-tauri/src/, web/src/, api/) for files modified in the last
   2 hours using `find {project}/ \( -path */src/* -o -path */lib/* -o -path */app/* -o -path */backend/* -o -path */frontend/src/* -o -path */components/* -o -path */api/* \) -newer {project}/memory/agents/pd-scratch.md -type f 2>/dev/null`.
3. Compare the detected changed/recent files against the delta's `## Mid-Flight` list.
4. **If ALL changed files are accounted for in the delta OR the delta lists them as mid-flight:**
   delta is valid — proceed with delta mode.
5. **If changed files exist that the delta does NOT list (mismatch detected):**
   downgrade to FULL SCAN MODE. The full scan is always safe; the delta is not trusted.
   Log: "Delta validation: mismatch detected — downgrading to FULL SCAN (N unlisted files)."

After passing the validation gate, proceed:
- Use the delta as the primary source of truth for was_doing, just_finished, decisions, mid-flight
- Read only: `{project}/memory/next-session.md` and `{project}/.claude/save-state-state.json`
- Skip the full baseline scan below — the delta covers it
- Skip Step 2 (mid-flight scan) — the delta lists mid-flight files directly
- For lessons: read only the lesson files mentioned in the delta (or project-relevant lessons if none listed)
- Emit: `bash ~/.claude/memory/metrics/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"save_state","mode":"delta","reads_skipped":5}'` (fire-and-forget)
- Proceed directly to Step 3 (active tasks) and Step 3b

**If no session delta exists, delta is marked INCOMPLETE, or delta timestamp > 2 hours ago**
(FULL SCAN MODE — always safe):

**Memory size guard (run before reading):**
```bash
MEMORY_SIZE=$(du -sk "{project}/memory" 2>/dev/null | awk '{print $1}')
if [ "${MEMORY_SIZE:-0}" -gt 2048 ]; then
  echo "WARN: memory dir is ${MEMORY_SIZE}KB (>2MB). Switching to capped read mode."
  LARGE_MEMORY=true
else
  LARGE_MEMORY=false
fi
```

If `LARGE_MEMORY=true`:
- Read `{project}/memory/decisions.md` HEAD only: `head -n 100 {project}/memory/decisions.md` (captures the most recent decisions pinned at top). Do NOT read the full file.
- Skip reading `{project}/memory/decisions-archive.md` entirely.
- Read all other baseline files normally (heartbeat, STATE.md, next-session.md, CLAUDE.md, save-state-state.json).
- Emit: `bash ~/.claude/memory/metrics/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"save_state","mode":"full_capped","reads_skipped":1}'` (fire-and-forget)
- Proceed: note was_doing from heartbeat + next-session.md; skip decisions.md rewrite (Step 6b appends only — see guard there).

If `LARGE_MEMORY=false`, read simultaneously:
- {project}/memory/heartbeat.md
- {project}/STATE.md (if exists)
- {project}/memory/decisions.md (if exists)
- {project}/memory/next-session.md (if exists)
- {project}/CLAUDE.md (if exists)
- {project}/.claude/save-state-state.json (if exists)
- ~/.claude/memory/lessons/*.md (project-relevant files only — match project slug to lesson filenames)

Note what was being worked on, what's mid-flight, and any blockers.
Emit: `bash ~/.claude/memory/metrics/emit-metric.sh '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"save_state","mode":"full","reads_skipped":0}'` (fire-and-forget)

## Step 2 — Find Mid-Flight Files
(Skip if delta mode was used in Step 1 — delta lists mid-flight directly.)
Scan: src/, lib/, app/, backend/, frontend/src/, components/, src-tauri/src/, web/src/, api/.
Look for TODO/FIXME comments, recently modified files, or anything half-done.
Report file paths with one-line descriptions.

## Step 3 — Scan Active Tasks
Read all files in {project}/memory/tasks/ongoing/*.md simultaneously.
Collect per task: title, status, priority, description, next action, blockers.
Report: how many active tasks, brief one-line per task.
If no tasks/ongoing/ directory exists, skip silently.

## Step 3b — Scan and Update Inter-Spawn Tasks Index
Read `{project}/memory/inter-spawn-tasks/index.md` — it is the SSOT for inter-spawn tasks.
Report: how many active inter-spawn tasks, brief one-line per task.
Then OVERWRITE the Active Summary section in index.md — replace it entirely with current active tasks only.
Completed tasks are NOT listed — moved to inter-spawn-tasks/completed/ and removed from the index.
Format: one bullet per active task (task ID, sender PD, brief description).
If no active inter-spawn tasks, replace with: "_(no active inter-spawn tasks)_"
If no inter-spawn-tasks/index.md exists, skip silently.

## Step 3c — Materialize Next Action (no-op session fix)

**Purpose:** Ensure the `Next:` action written to next-session.md always has a corresponding
file in `{project}/memory/tasks/ongoing/`. PD startup reads ONLY that folder; if no file
exists for the Next action, the PD finds nothing actionable and no-ops. This step closes that gap.

**Run after Step 3 (active tasks scan) and BEFORE writing next-session.md (Step 6).**
The `Next:` text used here is the one you have synthesized for Step 6.

### Match check

1. Take the `Next:` line that Step 6 will write.
2. Check for a task-id token in the Next line — match with regex `\b([A-Z]\d+|T\d+-\d+|F\d+)\b`
   (e.g. F22, T3-1, P1). If a token is found AND a file `{project}/memory/tasks/ongoing/*{token}*.md`
   exists → **MATCH** — skip materialization.
3. If no task-id token found (or no file matched): compare the first 5 significant words of
   the Next line (lowercase, strip punctuation) against each ongoing task's title or first line
   (case-insensitive). If substantial overlap (3+ of 5 words match) → **MATCH** — skip.
4. Otherwise → **NO MATCH**.

**Conservative bias:** when the match is ambiguous, treat it as NO MATCH and create the stub.
A redundant stub is cheap. A missed action causes a no-op session.

### On NO MATCH — write stub task file

Compute `{kebab-slug}`: take the Next line text, lowercase, replace non-alphanumeric runs with
hyphens, trim to 40 chars.

Write `{project}/memory/tasks/ongoing/next-action-{kebab-slug}.md`:

```
# {Next line text}

**Status:** ACTIVE — auto-materialized by save-state
**Created:** {YYYY-MM-DD}
**Priority:** P2
**Source:** next-session.md Next: line ({YYYY-MM-DD session date})

## Action
{verbatim Next: line text}

## Note
Auto-generated by save-state Step 3c because no ongoing task matched this
Next action. The next PD session will pick this up from tasks/ongoing/.
Expand into a fuller spec if the action needs decomposition.
```

**Idempotency:** if `{project}/memory/tasks/ongoing/next-action-{kebab-slug}.md` already
exists with the same Next text → overwrite (do not create a duplicate). Stale
`next-action-*.md` files whose action no longer matches the current Next line → leave them
(a real PD will complete/archive them); do NOT auto-delete.

**Log the action** (one line is enough): "Step 3c: created next-action-{kebab-slug}.md"
or "Step 3c: matched existing task {filename} — no stub needed".

## Step 4 — Write Session Log
Create or append to {project}/memory/sessions/YYYY-MM-DD.md:

## Session — YYYY-MM-DD HH:MM UTC

**was_doing**: [what was being worked on]
**just_finished**: [what completed before stopping]
**doing_next**: [specific next action]

### Mid-Flight
{format mid_flight list}

### Decisions Made
{format decisions list}

### Blockers Hit
{format blockers list}

### Notes
- [any context from this session]

## Step 5 — Update Heartbeat (overwrite Session End only)
Read {project}/memory/heartbeat.md.
OVERWRITE the Session End section. Keep Phase Status + Blockers intact.
Append only the new Session End block below the existing Phase Status + Blockers.
Old Session End blocks are NOT carried forward — they live in sessions/YYYY-MM-DD.md.

## Session End — YYYY-MM-DD HH:MM UTC

### Completed This Session
- [item from just_finished]

### In Progress
- [item from was_doing]

### Top 3 Priorities
1. [priority 1]
2. [priority 2]
3. [priority 3]

### Blockers
{format blockers list}

## Step 6 — Write next-session.md (CRITICAL — write BEFORE decisions rewrite)

**Ordering rationale:** next-session.md is written here — after session log and heartbeat
are captured (Steps 4-5), but BEFORE the decisions rewrite (Step 6b) and all subsequent
steps. This ensures the handoff file is complete even if the subagent hangs or dies during
the heavy decisions.md read/rewrite. Step 0 wrote a tombstone at the very start; this step
replaces it with the full, real content as soon as the minimum required data is available.

**For the Decisions field:** if you already read decisions.md in full scan mode (Step 1,
`LARGE_MEMORY=false`), use the top 2 locked decisions from that earlier read. If
`LARGE_MEMORY=true` (decisions were not fully read), use the head-only excerpt read in
Step 1 or write "see decisions.md" — do NOT block this step by reading decisions.md again.

Overwrite {project}/memory/next-session.md. This is the ONLY file pd-resume reads
at startup, so it must be self-contained. Max 15 lines. Use compact key: value format
(no ## headers — they waste tokens).

**Before writing:** scan `{project}/memory/inter-spawn-tasks/incoming/` for any `.md`
files. List each as a "Pending inbound" line in the `Delegated` field. These are
unread inter-spawn tasks that the next PD session MUST see — without this sweep,
they are invisible on resume (the contract in the identity file says "incoming checked
FIRST" but pd-resume only reads next-session.md, so the contract is only honored if
next-session.md carries the pending inbound list).

```
# {slug}
Phase: [current phase or status]
Next: [specific next action — one sentence, be precise]
Blockers: [one per line, or "none"]
Decisions: [top 2 locked decisions from decisions.md, one per line, or "see decisions.md"]
Mid-flight: [1-2 files with one-line description, or "none"]
Delegated: [pending inter-spawn tasks with status, or "none"]
Pending inbound: [list each incoming/*.md filename with 1-line title, or "none"]
Last saved: YYYY-MM-DD
```

Rules for next-session.md:
- Be specific: "deploy marketing pipeline to Vercel" not "continue deployment"
- `Next:` MUST name a concrete target (file, task, action, URL, or agent). Vague entries like "continue work", "review progress", "continue development" are INVALID — rewrite with a specific target. Valid: "run eval suite on evals/cases.jsonl and fix failing cases". Invalid: "continue eval work".
- Include ONLY actionable context — no session history, no completed items
- Decisions: only locked decisions that affect the Next action (use already-read data, do not re-read decisions.md here)
- Delegated: only pending/blocked tasks, not completed ones
- Pending inbound: list ALL files currently in inter-spawn-tasks/incoming/ — these
  are unprocessed tasks. If none, write "none" — do not omit the field
- If no decisions or delegated tasks exist, write "none" — do not omit the field

## Step 6b — Decisions Record
If `LARGE_MEMORY=true` (set in Step 1): skip reading decisions.md entirely. Only append the new decisions from this session using a targeted append — do NOT read the full file first. Write the new entries directly to the bottom of the file.

If `LARGE_MEMORY=false`: read {project}/memory/decisions.md. Append any new decisions not already recorded.

## Step 6c — Decisions Archive (auto-prune)
After appending new decisions, count lines in {project}/memory/decisions.md:
```bash
LINE_COUNT=$(wc -l < "{project}/memory/decisions.md" 2>/dev/null || echo 0)
echo "decisions.md: ${LINE_COUNT} lines"
```

If `LINE_COUNT > 200`:
1. Extract the top 60 lines (most recent pinned decisions) as the new active content.
2. Extract lines 61+ as the batch to archive.
3. Append the archived batch to `{project}/memory/decisions-archive.md` with a header:
   `## Archived YYYY-MM-DD (auto-prune): decisions moved from decisions.md lines 61+`
   If decisions-archive.md does not exist, create it first.
4. Rewrite decisions.md with only the top 60 lines + an archive pointer line:
   `_(YYYY-MM-DD decisions auto-archived to memory/decisions-archive.md)_`

If `LINE_COUNT ≤ 200`: skip silently.

**Note:** This prune runs on every save-state when the file is large, appending to the existing archive each time. The "skip if archive exists" behavior is REMOVED — the archive grows incrementally with each prune pass.

## Step 7 — Lessons Sync

## Step 8 — Update STATE.md (OPTIONAL — backwards compat only)
If {project}/STATE.md already exists, update its Last Session section.
**Do NOT create STATE.md for new projects.** next-session.md is the SSOT for startup.

## Step 9 — (MOVED) next-session.md now written at Step 6
This step is intentionally left as a no-op placeholder for backwards compatibility with
references to "Step 9" in pd-coordinator.md and coord.md. next-session.md is written
at Step 6 (before decisions rewrite and all subsequent steps) — not here.

## Step 10 — Reset Turn Counter
Update {project}/.claude/save-state-state.json:

{ "turn_count": 0, "last_turn_at": "[current timestamp]", "last_saved_at": "[current timestamp]", "last_session_date": "YYYY-MM-DD" }

Skip if the file doesn't exist.

## Step 11 — Dispatch Morpheus Brief

**EXCEPTION: If the project slug is "morpheus", skip this step entirely. Do not write a self-message.**

After completing Steps 1-10, generate and write a save-state brief to morpheus's incoming inter-spawn-tasks folder.

**Brief format (exact structure required):**
```
project: {slug}
status:
- {bullet 1: current phase and what was saved}
- {bullet 2: what changed or what was worked on this session}
- {bullet 3: blockers and next action}
```

Derive the 3 bullets from what you already synthesized for next-session.md:
- Bullet 1: Phase + what the session captured (e.g. "Active — save-state written with 2 mid-flight files")
- Bullet 2: What changed / was worked on (from was_doing / just_finished)
- Bullet 3: Top blocker (or "no blockers") and the Next action from next-session.md

**Write the file to:**
`~/projects/morpheus/memory/inter-spawn-tasks/incoming/save-state-brief-{YYYYMMDD-HHMMSS}-{slug}.md`

Where `{YYYYMMDD-HHMMSS}` is the current timestamp in GMT+7.

Write only the brief content — no other headers or metadata. Example:
```
project: system-improvement
status:
- Active — save-state written, session captured 2 mid-flight tasks and 1 decision
- Worked on Vercel/Supabase P1-P10 fix plan; awaiting Tekki row-by-row approval
- Blocker: Tekki approval needed. Next: apply approved rows via Coord after approval
```

If `~/projects/morpheus/memory/inter-spawn-tasks/incoming/` does not exist, create it first.

## Step 11a — Confirm

Before outputting the confirmation, emit the save_state_complete event (F13 — completion normalization):

```bash
bash ~/.claude/memory/metrics/emit-metric.sh \
  '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","event":"save_state_complete","project":"'"${SLUG:-unknown}"'","mode":"'"${SAVE_MODE:-unknown}"'"}'
```

Where `SLUG` is the project slug being saved and `SAVE_MODE` is the mode detected in Step 1
(`delta`, `full`, `full_capped`, `spawning_subagent`, or `spawning`).
This emit is fire-and-forget. If the emit script is missing, skip silently and proceed.

Output only: save-state done!
Then stop. No further narration.

## Step 11b — Update Project Knowledge Graph (caller-side, background, fire-and-forget)

After the subagent says "save-state done!", update the per-project knowledge graph
so curator agents can query it in future sessions.

```bash
# Only run if graphify is installed and memory dir has files
if command -v graphify >/dev/null 2>&1 && [ -d "{project}/memory" ]; then
  cd "{project}"
  # Exclude binary/image directories and graphify output dir from scan.
  # brand/ may contain images (large binaries). qa/screenshots/ and brand/reference-assets/
  # are never useful for knowledge extraction and can push memory/ past 10MB.
  # graphify-out/ is output, not input — scanning it causes recursive loops.
  graphify memory/ --update --no-viz \
    --exclude "brand/" \
    --exclude "qa/" \
    --exclude "graphify-out/" \
    2>/dev/null || \
  graphify memory/ --update --no-viz 2>/dev/null || true
  # Note: if --exclude flag is not supported by installed version, falls back to plain scan.
  # Upgrade graphify to support --exclude for full benefit.

  # Merge into unified graph
  if [ -f "memory/graphify-out/graph.json" ] && [ -f ~/.claude/graphify-out/unified/graph.json ]; then
    graphify merge-graphs ~/.claude/graphify-out/unified/graph.json \
      memory/graphify-out/graph.json --in-place 2>/dev/null || true
  fi
fi
```

Run with `run_in_background: true`. Best-effort — skip silently if graphify
is unavailable or memory/ has no changes since last run. The `--update` flag
makes this incremental — only re-extracts files changed since last run.

## Step 12 — Fire Pinecone Upsert (caller-side, background, fire-and-forget)

After the subagent says "save-state done!", the caller fires the Pinecone upsert.
Read the session files written by the subagent, build the JSON blob, fire it with
`run_in_background: true`. Best-effort — dies silently if the venv or script is missing.

## Step 13 — Write session node to unified graph (caller-side, background, fire-and-forget)

After Step 12, fire a background Bash call that appends a session node to the unified
knowledge graph at `~/.claude/graphify-out/unified/graph.json`. This makes the graph
temporal and enables cross-session pattern detection.

No graphify CLI command exists for adding individual nodes — use a Python one-liner
that directly edits the JSON file.

```bash
python3 - <<'PYEOF'
import json, datetime, re, pathlib, sys

graph_path = pathlib.Path.home() / ".claude/graphify-out/unified/graph.json"
if not graph_path.exists():
    sys.exit(0)

try:
    with open(graph_path) as f:
        graph = json.load(f)
except (json.JSONDecodeError, OSError):
    sys.exit(0)

# --- resolve slug and date from save-state-state.json or fall back to cwd ---
import os
slug = pathlib.Path(os.environ.get("PWD", ".")).name
date_str = datetime.date.today().isoformat()

# Try to read last_session_date from state file
state_path = pathlib.Path(os.environ.get("PWD", ".")) / ".claude/save-state-state.json"
if state_path.exists():
    try:
        state = json.loads(state_path.read_text())
        slug_candidate = state.get("slug", slug)
        if slug_candidate:
            slug = slug_candidate
        date_candidate = state.get("last_session_date", date_str)
        if date_candidate:
            date_str = date_candidate
    except Exception:
        pass

node_id = f"session_{re.sub(r'[^a-z0-9]', '_', slug.lower())}_{date_str.replace('-', '_')}"
session_file = f"memory/sessions/{date_str}.md"

node = {
    "id": node_id,
    "label": f"{slug} session {date_str}",
    "file_type": "session",
    "source_file": session_file,
    "source_location": None,
    "source_url": None,
    "captured_at": date_str,
    "author": None,
    "contributor": None,
}

nodes = graph.setdefault("nodes", [])
edges = graph.setdefault("links", [])

if any(n["id"] == node_id for n in nodes):
    sys.exit(0)  # already recorded this session

nodes.append(node)

# --- scan session log for skill / agent / file mentions → add edges ---
session_path = pathlib.Path(os.environ.get("PWD", ".")) / session_file
if session_path.exists():
    try:
        text = session_path.read_text()
    except OSError:
        text = ""

    # Build a node ID lookup for fast matching
    node_ids = {n["id"] for n in nodes}

    # Match skill invocations like /save-state, /recall, /graphify
    skill_mentions = set(re.findall(r"/([a-z][a-z0-9-]+)", text))
    for skill in skill_mentions:
        target_id = f"skill_{re.sub(r'[^a-z0-9]', '_', skill)}"
        edges.append({
            "source": node_id,
            "target": target_id,
            "relation": "used_skill",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": session_file,
            "weight": 1.0,
        })

    # Match PD / coord agent name patterns like ltv-pd, auth-Gatekeeper
    agent_mentions = set(re.findall(r"\b([a-z][a-z0-9-]+-(?:pd|coord|exec))\b", text, re.IGNORECASE))
    for agent in agent_mentions:
        target_id = f"agent_{re.sub(r'[^a-z0-9]', '_', agent.lower())}"
        edges.append({
            "source": node_id,
            "target": target_id,
            "relation": "worked_with",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": session_file,
            "weight": 1.0,
        })

    # Match decision references (## Decision, decided, decision:)
    if re.search(r"(?i)(decision|decided|resolved)", text):
        decision_id = f"decisions_{re.sub(r'[^a-z0-9]', '_', slug.lower())}"
        edges.append({
            "source": node_id,
            "target": decision_id,
            "relation": "recorded_decision",
            "confidence": "INFERRED",
            "confidence_score": 0.8,
            "source_file": session_file,
            "weight": 1.0,
        })

    # Match file paths mentioned in session (memory/*.md, src/*, etc.)
    file_mentions = set(re.findall(r"(?:memory|src|lib|app)/[a-zA-Z0-9/_-]+\.(?:md|ts|py|rs|json)", text))
    for fpath in list(file_mentions)[:10]:
        stem = re.sub(r'[^a-z0-9]', '_', pathlib.Path(fpath).stem.lower())
        target_id = f"{stem}"
        if target_id in node_ids:
            edges.append({
                "source": node_id,
                "target": target_id,
                "relation": "modified",
                "confidence": "INFERRED",
                "confidence_score": 0.7,
                "source_file": session_file,
                "weight": 1.0,
            })

# --- incremental merge trigger: every 5 new session nodes ---
session_nodes = [n for n in nodes if n.get("file_type") == "session"]
if len(session_nodes) % 5 == 0:
    # Write a flag file; the merge itself runs as a separate background call
    trigger_path = pathlib.Path.home() / ".claude/graphify-out/.session_merge_needed"
    trigger_path.write_text(str(len(session_nodes)))

with open(graph_path, "w") as f:
    json.dump(graph, f, indent=2)

print(f"[save-state] session node written: {node_id}")
PYEOF
```

Run this Bash block with `run_in_background: true`. Best-effort — if `graph.json` is
missing, malformed, or python3 is unavailable, the script exits silently without
affecting save-state output.

After the Python block completes, check for the merge trigger flag and fire a
separate background merge if needed:

```bash
FLAG=~/.claude/graphify-out/.session_merge_needed
if [ -f "$FLAG" ]; then
  rm -f "$FLAG"
  graphify merge-graphs ~/.claude/graphify-out/unified/graph.json --in-place 2>/dev/null || true
fi
```

Also run this second block with `run_in_background: true`.
