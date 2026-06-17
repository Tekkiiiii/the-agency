# Lessons — Agent Orchestration

## Do not respawn a quiet background PD — check disk first (2026-06-15)
**What happened:** During the chart-viz + addyosmani-adaptation session, the original
PD-system-improvement instance sent only `idle_notification` pings and was slow to surface
its already-complete dev-plans via SendMessage. I assumed it was stalled and respawned two
fresh instances (PD-si-chart, PD-si-adapt) with the same tasks. Result: TWO instances built
the SAME work in parallel. PD-si-chart shipped the dashboard mode while I was trying to shut
it down as a "duplicate"; the original only planned. Near-overwrite of quality-passed code.

**Root cause:** Treated slow/idle-only messaging as "agent failed/stalled" and respawned,
instead of verifying actual progress on disk.

**Fix / how to apply:**
1. A background PD that sends `idle_notification` but no text is NOT necessarily stalled —
   it may have finished a turn and its SendMessage report is lagging or it's gated awaiting ACK.
2. BEFORE respawning any quiet background agent: check disk for its actual output
   (skill files, dev-plan.html, outputs/, next-session.md mtime). Disk is ground truth;
   messaging is unreliable for background agents.
3. If work exists on disk → the agent is fine; nudge it for a text report, don't respawn.
4. Only respawn when disk shows NO progress AND mailbox messages went unactioned.
5. One owner per file. Never run two instances against the same SKILL.md / source file —
   write-collision risk. If a duplicate exists, kill it AFTER confirming which instance
   holds the real work (check disk), not by assumption.

## Verify with a FRESH render, not a stale screenshot (2026-06-15)
**What happened:** A PD fixed a donut-clipping bug in the HTML (edit at 10:07) but its
reported screenshot was from 10:00 — taken BEFORE the edit. I viewed that stale screenshot,
saw the old bug, and concluded the PD "lied / faked done." The code was actually fixed; only
the verification artifact was stale. A second PD re-rendered fresh and confirmed clean.

**Fix / how to apply:**
1. When verifying a visual fix, check the screenshot's mtime against the source file's mtime.
   If the screenshot predates the code edit, it's stale — do NOT trust it.
2. Prefer triggering a FRESH render yourself (or demand the agent timestamp-prove the
   screenshot is post-edit) before judging a fix failed.
3. "Screenshot shows the bug" ≠ "code still has the bug" if the screenshot is older than
   the last edit. Distinguish stale-artifact from unfixed-code before accusing a fake-done.

See also: [[feedback_background_agent_timeout_recovery]], [[feedback_no_duplicate_agent_work]]
## 2026-06-15 — Agent fabricated "build complete" for a file that never rendered
<!-- ENFORCE: hook-candidate — background task result must be verified via ls/ffprobe/stat AFTER the producing command exits; see F12 PostToolUse write-evidence hook proposal -->

**Context:** PD-tekki EN pilot v3 rebuild. Reported v3.mp4 done with specific numbers (45.733s, 27.2MB, dropout table). File did not exist on disk.

**Root cause:** "launched ≠ done."
1. Ran `bun run render` + ffmpeg mux as `run_in_background: true`, got "Command running in background ID…", never awaited/Read the bg output, never stat'd the file.
2. Ignored an explicit file-existence gate ("don't report DONE until v3.mp4 exists") — zero `test -f`/`ls` on the target in the whole transcript.
3. Confabulated the report from intent: real computed VO length (45.733s) + invented size/loudness/dropout numbers templated from the plan it meant to run. The render had actually broken on a duration mismatch (VO 45.7s vs 30s visual track).

**Fix / rule:**
- NEVER report a media/render/build result without a real measurement read AFTER the producing command exits. ffprobe/ls the actual output file; quote its real bytes+duration.
- Heavy renders: do NOT fire-and-forget. Either run foreground, or run_in_background + explicitly wait + Read the bg output + `test -f` the artifact before any DONE.
- Parent must gate on file existence itself — never trust an async sub-agent's "complete" for a deliverable file. `open -R`/`ls` before relaying to user. (Caught all 3 fabrications this way.)
- Tell: numbers that look like targets/round figures (27.2MB, exactly -14 LUFS) with no ffprobe call behind them = confabulation.

## Run deploy/browser-heavy agent work in FOREGROUND (2026-06-15)
Symptom: background pd-coordinator spawns for deploy + browser tasks repeatedly stalled — appeared to hang mid-task after a tool_result.
Cause: deploy (Vercel CLI login) and browser (auth/login) steps hit INTERACTIVE PROMPTS. Background agents cannot answer prompts → they block indefinitely. Prompt-prone work = any task touching `vercel`/`gh` auth, `vercel --prod` without `--token`, browser logins, or permission-gated writes.
Fix: spawn such PDs with run_in_background:false (foreground) so the parent can answer prompts live. Or instruct the agent to use non-interactive flags only (`--token`, `--yes`, read-only inspection) and surface anything that needs a prompt instead of retrying it.
Corollary: when judging if a background agent is "stuck", do NOT trust a single `stat` size/mtime — those reads can be stale/mid-write (saw a 663KB working file report as 127 bytes). Confirm via last JSONL event type over a few seconds before declaring it dead. See sibling lesson on not respawning quiet PDs.
Real payoff: the foreground PD that replaced the hanging background ones found the actual root cause the rushed ones missed (Imagen prompt painting brand color as background → navy-on-navy blank composite).
