#!/usr/bin/env python3
"""Slash command handler for /scout — runs the Project Expansion Scout cycle."""
import json
import sys
from pathlib import Path

STATE_FILE = Path.home() / ".claude" / "memory" / "expansion-scouts" / "voting-state.json"
PROMPT = """
Run the Project Expansion Scout cycle now.

1. Read ~/.claude/memory/expansion-scouts/voting-state.json for current state
2. Read ~/.claude/memory/medium-term.md to get the active project list
3. For each active project:
   a. Read its PROJECT.md
   b. Scan source code for expansion signals (TODOs, FIXME, scope underruns, stale focus items, unimplemented features)
   c. If an opportunity is found, write the expansion draft to ~/.claude/memory/expansion-scouts/{project}/current-draft.md
4. If any draft was written:
   a. Assemble the BOD council (2-wave spawn: wave1=engineering-lead,design-lead,game-development-lead,marketing-lead,sales-lead,paid-media-lead; wave2=product-lead,pm-lead,testing-lead,operations-lead,specialized-lead,spatial-lead)
   b. Present each draft for a vote (approve/revise/reject)
5. Check threshold (approval/votes >= 0.80):
   - If approved: append to {project}/PROJECT.md under ## Expansion Phases, log to {project}/memory/decisions.md, archive draft to history/
   - If revise majority: incorporate revision notes, update draft, re-vote (max 5 cycles)
   - If reject majority after 5 cycles: archive with rejection reason
6. Update voting-state.json with last_scan date and results
7. Report concise summary.
"""

try:
    # Update last_scan timestamp in voting-state.json
    from datetime import date
    state = json.loads(STATE_FILE.read_text())
    state["last_scan"] = str(date.today())
    STATE_FILE.write_text(json.dumps(state, indent=2))
    print("Scout triggered. last_scan updated.")
    print("Full cycle: scan projects -> draft -> BOD consult -> vote -> update PROJECT.md")
except Exception as e:
    print(f"Warning: could not update voting-state.json: {e}")
    print("The expansion scout will run its full cycle when invoked.")
