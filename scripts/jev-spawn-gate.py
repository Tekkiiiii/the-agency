#!/usr/bin/env python3
"""jev-spawn-gate.py: the optional ENFORCER for binding Jev skill routing on spawns. Ships DISABLED.

Part of the opt-in skill router (scripts/skill-route/README.md). Nothing here does anything unless
AGENCY_SKILL_ROUTER is exactly "1" (the same rule as skill-route.py). The spawn-ledger mod
(mods/spawn-ledger) calls this script from its `agent.spawn` hook before the model pin. Reads ONE JSON object
on stdin:

  {tool_use_id, subagent_type, description, prompt, parent_agent, parent_spawn_id, fork, is_teammate, workflow}

and prints exactly ONE JSON line on stdout (nothing else, stderr silent), always exit 0:

  {"action": "pass"|"rewrite"|"deny", "prompt"?: "<rewrite: the FULL new prompt>", "deny"?: "<deny: message for the
   spawner>", "note"?: "<one line for the spawner>", "route_id"?: "<8 hex>", "reason"?: "<verdict_source or rule>"}

Flow:
  0. DISABLED (the default): AGENCY_SKILL_ROUTER is not "1" -> print {"action":"pass"} and exit 0. No network, no
     Jev or Haiku call, no subprocess, no state write, no router import.
     FAIL OPEN. Any exception -> {"action":"pass"}. A router timeout / error is an OUTAGE, never a deny.
     OFF SWITCHES (pass, nothing else done): env JEV_GATE_OFF=1; the file jev-gate.off in {root}/state or in the
     router state dir ($SKILL_ROUTE_STATE_DIR, default {root}/state/skill-route); {root}/.hook-profile == minimal.
     SKILL_ROUTE_CHILD=1 (the Haiku child of jev_client) also passes: the child's own spawns must never recurse
     into routing. {root} = the agency root ($AGENCY_HOME, else $CLAUDE_CONFIG_DIR, else the default install dir).
  1. fork / is_teammate / workflow / not jev_spawn.is_binding(subagent_type) -> pass, untouched.
  2. The prompt has `Jev[r=<id>]` and the route cache has <id> -> use the cached Jev result, NO routing call.
     Otherwise skill-route.gate_route() under a 10 s deadline (daemon thread). Timeout / exception -> outage:
     evaluate(outage=True) -> pass when the prompt already carries a Jev line, else rewrite that appends
     `Jev: unavailable - router=timeout|error`.
  3. jev_spawn.evaluate() + apply_decision(). A Jev line whose id is not in the cache is treated as id-less, so a
     rewrite replaces it with the fresh `Jev[r=<id>]` and the post-spawn recorder hits the cache (one Jev call total).
     On deny: cache_bump_denies(id); evaluate's loop guard turns the 3rd deny for one id into pass (reason deny_cap).
  4. SECOND loop guard, per spawner + task (a spawner that re-issues WITHOUT the Jev line gets a fresh route id and a
     fresh Jev call every time, so the per-id counter never trips): key = jev_spawn.spawner_key(parent_spawn_id or
     parent_agent or "root", the routed text). Effective denies = max(route-id denies, spawner denies); a deny bumps
     BOTH; same cap (the 3rd deny-worthy call passes, reason deny_cap). State: {state}/jev-gate-denies/<key>.json,
     TTL 1h. Any failure in the key / counter is silent: that guard is skipped, the per-id guard still works.

Test overrides: JEV_GATE_DEADLINE (seconds, default 10), AGENCY_HOME (the root), SKILL_ROUTE_STATE_DIR, plus every
skill-route / jev_client variable (SKILL_ROUTE_SKILLS_DIR, SKILL_ROUTE_OVERLAY, SKILL_ROUTE_LOG,
SKILL_ROUTE_SHADOW_LOG, JEV_ENDPOINT, JEV_USAGE_LOG, ...).

The gate never writes jev-feedback.jsonl (the recorder does). It DOES append ONE `"event": "gate_deny"` JSON line to the
skill-route shadow log ($SKILL_ROUTE_SHADOW_LOG) on every deny and every deny_cap pass (F4), written with skill-route's
own fail-silent appender. FAIL OPEN: any error in building or writing the line is swallowed and never changes the
output, stdout or stderr. Keys: ts, event, decision ("deny"|"deny_cap"), route_id, rule (the evaluate() reason), gate,
router, none_fired, confidential, jev_skills, spawner_skills, subagent_type, parent_agent, spawner (parent_spawn_id or
parent_agent or "root"), denies_after (the deny counter after this call), task_excerpt (first 200 chars of the routed
text, whitespace squashed and redacted; "[REDACTED:confidential]" when Jev flagged the prompt confidential). Pass /
rewrite outcomes write nothing.
"""
import importlib.util
import json
import os
import re
import sys
import threading
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
DEADLINE_DEFAULT = 10.0


SWITCH_ENV = "AGENCY_SKILL_ROUTER"
PASS_LINE = '{"action": "pass"}'


def router_enabled():
    """True only when AGENCY_SKILL_ROUTER is exactly "1". Same rule as skill-route.py router_enabled()."""
    return os.environ.get(SWITCH_ENV) == "1"


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


def _root():
    return agency_root(os.path.expanduser("~"))


def _state_dir():
    """The router state dir, the same one skill-route.py and jev_spawn.py use."""
    return os.environ.get("SKILL_ROUTE_STATE_DIR") or os.path.join(_root(), "state", "skill-route")


def kill_switch():
    if os.environ.get("JEV_GATE_OFF") == "1":
        return "env JEV_GATE_OFF"
    if os.environ.get("SKILL_ROUTE_CHILD") == "1":
        return "SKILL_ROUTE_CHILD"
    for d in (os.path.join(_root(), "state"), _state_dir()):
        if os.path.exists(os.path.join(d, "jev-gate.off")):
            return "flag file jev-gate.off"
    try:
        with open(os.path.join(_root(), ".hook-profile"), encoding="utf-8") as f:
            if f.read().strip() == "minimal":
                return "hook-profile minimal"
    except Exception:
        pass
    return ""


def _deadline():
    try:
        return max(0.05, float(os.environ.get("JEV_GATE_DEADLINE", DEADLINE_DEFAULT)))
    except ValueError:
        return DEADLINE_DEFAULT


def _load_skill_route():
    spec = importlib.util.spec_from_file_location("skill_route_gate", os.path.join(HERE, "skill-route.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _route_with_deadline(sr, prompt, description, subagent_type, parent_agent):
    """gate_route in a daemon thread. Returns (result_tuple|None, error_label). error_label is "" on success."""
    box = {}

    def work():
        try:
            box["r"] = sr.gate_route(prompt, description, subagent_type, parent_agent)
        except BaseException as e:  # MenuError included: outage, never a deny
            box["e"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(_deadline())
    if t.is_alive():
        return None, "timeout"
    if "r" in box:
        return box["r"], ""
    return None, "error"


def _slash(skills):
    return ", ".join("/" + str(s).lstrip("/") for s in skills)


def _note(dec, rid, jev):
    src = dec.get("verdict_source")
    if src == "deny_cap":
        return "jev-gate: deny cap reached for r=%s; spawn allowed unreviewed (%s)" % (rid or "-", dec.get("reason"))
    if src == "jev_unavailable":
        return "jev-gate: Jev unavailable (%s); recorded unreviewed" % dec.get("reason")
    if src == "auto_default":
        return "jev-gate: injected Jev default skills %s (gate pass)" % _slash(dec.get("inject_skills") or [])
    if src == "auto_match":
        return "jev-gate: Skills match Jev (gate pass); injected Jev line, recorded accept"
    if src == "auto_empty":
        return "jev-gate: Jev found nothing and no Skills named; injected Jev line, recorded accept"
    if src == "confidential_local":
        return "jev-gate: confidential prompt routed locally (grep), not reviewed by Jev; injected unavailable line"
    if dec.get("inject_skills"):
        return "jev-gate: accept with no Skills; injected Jev skills %s" % _slash(dec["inject_skills"])
    if dec.get("inject_line"):
        return "jev-gate: set the route id on your Jev line (r=%s)" % (rid or "-")
    return ""


def _spawner_guard_key(sr, jev_spawn, spawner, prompt, description):
    """Key of the per-spawner+task deny guard, built from the SAME text the gate routes on (skill-route._spawn_text:
    Jev line, Skills clause and slash tokens stripped), so a re-issue maps to one key whatever line/skills it carries.
    "" on any failure: the second guard is then skipped (fail open)."""
    try:
        _full, text = sr._spawn_text(prompt, description, list(sr.load_menu()["skills"]))
        return jev_spawn.spawner_key(spawner, text)
    except Exception:
        return ""


def _log_gate_deny(sr, jev_spawn, decision, dec, rid, jev, actual, denies_after, subagent_type, parent_agent, spawner,
                   prompt, description):
    """Append ONE gate_deny line to the shadow log. Fail open: ANY exception is swallowed, nothing is printed, the
    gate output is never affected (callers ignore the return value)."""
    try:
        confidential = bool(jev.get("confidential"))
        excerpt = "[REDACTED:confidential]"
        if not confidential:
            try:
                _full, text = sr._spawn_text(prompt, description, list(sr.load_menu()["skills"]))
                excerpt = sr._excerpt(text)
            except Exception:
                excerpt = ""
        sr._append_jsonl(sr._shadow_log_path(), {
            "ts": sr._now_iso(), "event": "gate_deny", "decision": decision, "route_id": rid or "",
            "rule": dec.get("reason"), "gate": jev.get("gate"), "router": jev.get("router"),
            "none_fired": bool(jev.get("none_fired")), "confidential": confidential,
            "jev_skills": list(jev.get("skills") or []), "spawner_skills": list(actual or []),
            "subagent_type": subagent_type, "parent_agent": parent_agent, "spawner": spawner,
            "denies_after": int(denies_after or 0), "task_excerpt": excerpt})
    except BaseException:
        pass


def decide(raw):
    """Pure-ish core: raw stdin text -> the output dict. May raise; main() fails open."""
    if not router_enabled():  # shipped disabled: no kill-switch file reads, no imports, no state, no network
        return {"action": "pass"}
    if not raw or not raw.strip():
        return {"action": "pass"}
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {"action": "pass"}
    if kill_switch():
        return {"action": "pass"}
    if data.get("fork") or data.get("is_teammate") or data.get("workflow"):
        return {"action": "pass"}
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import jev_spawn
    subagent_type = data.get("subagent_type")
    subagent_type = subagent_type if isinstance(subagent_type, str) else ""
    if not jev_spawn.is_binding(subagent_type, fork=False):
        return {"action": "pass"}

    prompt = data.get("prompt")
    prompt = prompt if isinstance(prompt, str) else ""
    description = data.get("description")
    description = description if isinstance(description, str) else ""
    parent_agent = data.get("parent_agent")
    parent_agent = parent_agent if isinstance(parent_agent, str) else ""

    if not prompt.strip() and not description.strip():  # nothing to route
        return {"action": "pass"}

    sr = _load_skill_route()
    spawner = data.get("parent_spawn_id")
    spawner = spawner if isinstance(spawner, str) and spawner else (parent_agent or "root")
    skey = _spawner_guard_key(sr, jev_spawn, spawner, prompt, description)
    line = jev_spawn.parse_verdict_line(prompt)
    cached = jev_spawn.cache_get(line["id"]) if line and line.get("id") else None
    outage = None
    if cached:
        rid = cached.get("route_id") or line["id"]
        jev = dict(cached)
        denies = int(cached.get("denies") or 0)
        actual = sr._actual_skills(prompt, list(sr.load_menu()["skills"]))  # MenuError -> fail open (pass)
    else:
        got, err = _route_with_deadline(sr, prompt, description, subagent_type, parent_agent)
        if got is None:  # outage: router timeout / error
            rid, denies, outage = "", 0, True
            jev = {"skills": [], "gate": None, "router": err, "none_fired": False, "confidential": False,
                   "jev_down": True}
            try:
                actual = sr._actual_skills(prompt, list(sr.load_menu()["skills"]))
            except Exception:
                actual = []
        else:
            res, meta, actual = got
            rid = res.get("route_id") or ""
            denies = 0
            jev = {"skills": list(res.get("skills") or []), "gate": res.get("gate"), "router": res.get("router"),
                   "none_fired": bool(meta.get("none_fired")), "confidential": bool(meta.get("confidential")),
                   "jev_down": bool(res.get("jev_down"))}
        if line and line.get("id"):  # stale id, not in the cache: let a rewrite replace it with the fresh one
            line = dict(line, id=None)

    if skey:  # second guard: the stricter of the two counters decides
        denies = max(denies, jev_spawn.spawner_denies(skey))
    dec = jev_spawn.evaluate(jev, actual, line, route_id=rid, denies=denies, outage=outage)
    out = {"action": "pass"}
    if rid:
        out["route_id"] = rid
    if dec["decision"] == "deny":
        after = 0
        if rid:
            after = jev_spawn.cache_bump_denies(rid) or 0
        if skey:
            after = max(after, jev_spawn.spawner_bump_denies(skey) or 0)
        _log_gate_deny(sr, jev_spawn, "deny", dec, rid, jev, actual, after, subagent_type, parent_agent, spawner,
                       prompt, description)
        out.update(action="deny", deny=dec["deny_message"], reason=dec["reason"])
        return out
    if dec.get("verdict_source") == "deny_cap":
        _log_gate_deny(sr, jev_spawn, "deny_cap", dec, rid, jev, actual, denies, subagent_type, parent_agent,
                       spawner, prompt, description)
    if dec.get("verdict_source"):
        out["reason"] = "deny_cap" if dec["verdict_source"] == "deny_cap" else dec["verdict_source"]
    new_prompt = jev_spawn.apply_decision(prompt, dec) if dec["decision"] == "rewrite" else prompt
    if dec["decision"] == "rewrite" and new_prompt and new_prompt != prompt:
        out.update(action="rewrite", prompt=new_prompt)
    note = _note(dec, rid, jev)
    if note and (out["action"] == "rewrite" or dec.get("verdict_source") == "deny_cap"):
        out["note"] = note
    return out


def _utf8_stdio():
    """Node sends UTF-8 JSON (Vietnamese included); Windows' default stdio codec is the locale code page.
    stdout also gets a bare-LF newline: Windows text mode would turn our one JSON line's LF into CRLF (POSIX: unchanged)."""
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if hasattr(s, "reconfigure"):
                s.reconfigure(encoding="utf-8", **({"newline": "\n"} if s is sys.stdout else {}))
        except Exception:
            pass


def main():
    _utf8_stdio()  # before the devnull redirect below: real_out is the very object reconfigured here
    real_out = sys.stdout
    out = {"action": "pass"}
    timed_out = False
    try:
        warnings.simplefilter("ignore")
        devnull = open(os.devnull, "w")
        sys.stderr = devnull
        sys.stdout = devnull  # nothing but our one JSON line may reach the real stdout
        out = decide(sys.stdin.read())
        timed_out = out.get("reason") == "jev_unavailable"
    except BaseException:  # fail open, whatever it was
        out = {"action": "pass"}
    try:
        real_out.write(json.dumps(out) + "\n")
        real_out.flush()
    except Exception:
        pass
    if timed_out:  # a router thread may still be running; do not wait for it at interpreter shutdown
        os._exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
