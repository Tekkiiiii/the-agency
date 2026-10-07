"""claude_pricing.py — single source of truth for Claude token rates used by
hooks (cost-tracker.sh). USD per million tokens.

Verified live 2026-10-05 against https://platform.claude.com/docs/en/about-claude/pricing
Re-verify against that page before editing any rate; never quote prices from memory.

Model IDs look like "claude-opus-5-5", "claude-opus-5-5[1m]", "claude-sonnet-4-6",
"claude-haiku-4-5-20251001". Match is by family + version; an unknown version of a
known family falls back to that family's newest rate and reports rate_source
"family_fallback" so stale tables are visible instead of silently wrong.
Long context (1M) is billed at standard rates for 4.6+ models — no multiplier.
"""
import re

# (pattern, label, input, cache_write_5m, cache_write_1h, cache_read, output)
_RATES = [
    (r"fable-5-1|mythos-5-1", "fable-5.1", 10.00, 12.50, 20.00, 0.25, 50.00),
    (r"fable-5|mythos-5|mythos", "fable-5", 10.00, 12.50, 20.00, 1.00, 50.00),
    (r"opus-5-5", "opus-5.5", 4.00, 5.00, 8.00, 0.20, 20.00),
    (r"opus-5", "opus-5", 5.00, 6.25, 10.00, 0.50, 25.00),
    (r"opus-4-[5-9]", "opus-4.5+", 5.00, 6.25, 10.00, 0.50, 25.00),
    (r"opus-4", "opus-4/4.1", 15.00, 18.75, 30.00, 1.50, 75.00),
    (r"sonnet-5", "sonnet-5/5.5", 2.00, 2.50, 4.00, 0.20, 10.00),
    (r"sonnet-4", "sonnet-4.x", 3.00, 3.75, 6.00, 0.30, 15.00),
    (r"haiku-4-5", "haiku-4.5", 1.00, 1.25, 2.00, 0.10, 5.00),
    (r"haiku-3-5", "haiku-3.5", 0.80, 1.00, 1.60, 0.08, 4.00),
]
# Family fallback = newest known rate in the family.
_FAMILY = {
    "fable": "fable-5.1", "mythos": "fable-5.1", "opus": "opus-5.5",
    "sonnet": "sonnet-5/5.5", "haiku": "haiku-4.5",
}
_BY_LABEL = {r[1]: r for r in _RATES}


def rate_for(model):
    """Return (rate_dict, rate_source). rate_source: exact | family_fallback | unknown_default."""
    m = (model or "").lower()
    for pat, label, i, w5, w1, r, o in _RATES:
        if re.search(pat, m):
            return ({"label": label, "input": i, "cache_write_5m": w5,
                     "cache_write_1h": w1, "cache_read": r, "output": o}, "exact")
    for fam, label in _FAMILY.items():
        if fam in m:
            _p, lb, i, w5, w1, r, o = _BY_LABEL[label]
            return ({"label": lb, "input": i, "cache_write_5m": w5,
                     "cache_write_1h": w1, "cache_read": r, "output": o}, "family_fallback")
    # Unknown model id (e.g. "unknown", "<synthetic>") — price as the session default (Opus 5.5).
    _p, lb, i, w5, w1, r, o = _BY_LABEL["opus-5.5"]
    return ({"label": lb, "input": i, "cache_write_5m": w5,
             "cache_write_1h": w1, "cache_read": r, "output": o}, "unknown_default")


def cost_usd(model, input_tokens=0, output_tokens=0, cache_write_5m=0,
             cache_write_1h=0, cache_read=0):
    rt, _src = rate_for(model)
    return (input_tokens * rt["input"] + output_tokens * rt["output"]
            + cache_write_5m * rt["cache_write_5m"] + cache_write_1h * rt["cache_write_1h"]
            + cache_read * rt["cache_read"]) / 1_000_000


def usage_from_transcript(path):
    """Sum usage over a Claude Code transcript JSONL, deduplicated by message.id
    (one API message is written as several lines, one per content block, each
    repeating the same usage — summing per line overcounts).
    Returns dict with per-model breakdown and totals."""
    import json
    msgs = {}
    chars = {}
    first_ts = last_ts = None
    tool_uses = 0
    last_text = ""
    handback = ""
    session_id = ""
    with open(path, errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not session_id:
                session_id = e.get("sessionId", e.get("session_id", "")) or ""
            ts = e.get("timestamp")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            if e.get("type") != "assistant":
                continue
            msg = e.get("message", {}) or {}
            mid = msg.get("id") or e.get("uuid")
            if msg.get("usage"):
                msgs[mid] = (msg.get("model", "unknown"), msg["usage"])
            for b in msg.get("content", []) or []:
                if isinstance(b, dict):
                    bt = b.get("type")
                    if bt == "text":
                        chars[mid] = chars.get(mid, 0) + len(b.get("text", "") or "")
                    elif bt == "thinking":
                        chars[mid] = chars.get(mid, 0) + len(b.get("thinking", "") or "")
                    elif bt == "tool_use":
                        chars[mid] = chars.get(mid, 0) + len(json.dumps(b.get("input", {})))
                    if b.get("type") == "tool_use":
                        tool_uses += 1
                        # Final report delivered via SubagentHandback is the agent's
                        # real output (its last text block is often empty/preamble).
                        if b.get("name") == "SubagentHandback":
                            handback = (b.get("input") or {}).get("message", "") or handback
                    elif b.get("type") == "text" and b.get("text"):
                        last_text = b["text"]
    by_model = {}
    output_estimated = 0
    for mid, (model, u) in msgs.items():
        if model == "<synthetic>":
            continue
        cc = u.get("cache_creation") or {}
        w1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
        w5 = cc.get("ephemeral_5m_input_tokens", None)
        total_w = u.get("cache_creation_input_tokens", 0) or 0
        if w5 is None:
            w5 = max(total_w - w1, 0)
        b = by_model.setdefault(model, {"input": 0, "output": 0, "cache_write_5m": 0,
                                        "cache_write_1h": 0, "cache_read": 0, "messages": 0})
        b["input"] += u.get("input_tokens", 0) or 0
        # Transcripts store message_start usage: output_tokens is the streaming
        # start value (often 2-50), not the final count. Estimate from emitted
        # content (~3 chars/token; thinking may be redacted so this is a floor)
        # and take the larger. Flagged via output_estimated_messages.
        rep = u.get("output_tokens", 0) or 0
        est = chars.get(mid, 0) // 3
        if est > rep:
            output_estimated += 1
        b["output"] += max(rep, est)
        b["cache_write_5m"] += w5
        b["cache_write_1h"] += w1
        b["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        b["messages"] += 1
    tot = {"input": 0, "output": 0, "cache_write_5m": 0, "cache_write_1h": 0,
           "cache_read": 0, "cost_usd": 0.0}
    for model, b in by_model.items():
        for k in ("input", "output", "cache_write_5m", "cache_write_1h", "cache_read"):
            tot[k] += b[k]
        b["cost_usd"] = round(cost_usd(model, b["input"], b["output"], b["cache_write_5m"],
                                       b["cache_write_1h"], b["cache_read"]), 4)
        tot["cost_usd"] += b["cost_usd"]
    tot["cost_usd"] = round(tot["cost_usd"], 4)
    last_ctx = 0
    if msgs:
        _m, lu = list(msgs.values())[-1]
        last_ctx = ((lu.get("input_tokens", 0) or 0) + (lu.get("cache_read_input_tokens", 0) or 0)
                    + (lu.get("cache_creation_input_tokens", 0) or 0))
    return {"by_model": by_model, "totals": tot, "tool_uses": tool_uses,
            "output_estimated_messages": output_estimated, "final_context_tokens": last_ctx,
            "first_ts": first_ts, "last_ts": last_ts, "last_text": last_text, "handback_text": handback,
            "session_id": session_id}
