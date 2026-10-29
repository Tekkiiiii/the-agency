"""jev_stub.py - shared test helpers for the Jev client / skill-route / spawn-plan tests.

NOT a test file (name does not match test_jev*). Stdlib only; runs on /usr/bin/python3 (3.9) and 3.14.
Import from a test:

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # scripts/tests
    import jev_stub

Typical use (one temp env + one stub server + one fake `claude`, everything restored on exit):

    with jev_stub.jev_test_env() as env:
        # env.stub        JevStub (already started); env.stub.url, env.stub.count, env.stub.last_body
        # env.fake_claude path of the fake `claude` (JEV_HAIKU_CMD already points at it)
        # env.state_dir / env.usage_log / env.notify_log / env.env_file / env.flag   (paths)
        env.stub.set_mode("401")                     # switch mode at runtime
        res = jev_client.ask("state", questions, "skill-route")
        env.usage_records(); env.notify_lines(); env.flag_exists(); env.flag_info()
        jev_stub.fake_claude_records(env.fake_claude)    # one dict per fake-claude invocation

All env vars the client reads are set by jev_test_env: AGENCY_SKILL_ROUTER=1 (the router ships disabled),
AGENCY_HOME (the temp root, so no default path can reach a real install), SKILL_ROUTE_STATE_DIR, JEV_USAGE_LOG,
JEV_NOTIFY_LOG, JEV_ENV_FILE (BOGUS key, made-up literal - never a real key), JEV_ENDPOINT
(stub URL), JEV_NOTIFY=0, JEV_EMIT=0, JEV_HAIKU_CMD (fake claude). JEV_PURPOSE, JEV_MODEL and
SKILL_ROUTE_CHILD and CLAUDE_CONFIG_DIR are UNSET inside the context (set them via extra_env=). The previous values
of every touched variable are restored on exit.

Public API
----------
BOGUS_KEY                                  made-up key literal written to the temp env file
class JevStub(mode="ok", winner=None, winners=None, peak=0.8, score_level=2, slow_seconds=4.0,
              score_shape="float", model="jev-stub")
    .start() -> self        .stop()          also a context manager
    .url                    "http://127.0.0.1:<port>/v1/systemone"
    .set_mode(mode)         "ok" | "401" | "403" | "422" | "429" | "500" | "529" (any int string) |
                            "garbage" (200 + non-JSON) | "badshape" (200 + JSON without answers) |
                            "slow" (sleeps slow_seconds, then answers - exceeds a 2s client timeout)
    .count                  total requests received (thread-safe)
    .reset()                zero counter and clear captured bodies
    .requests               list of {"path","headers","body"(raw str),"json"(parsed|None),"mode"}
    .last_body              parsed JSON body of the last request (None if none / unparseable)
    .last_raw               raw text of the last request body
    .last_auth              Authorization header of the last request (the BOGUS key in tests)
    .winner / .winners / .peak / .score_level / .score_shape / .slow_seconds   mutable at runtime
        ok-mode choice answers: winner = winners.get(question_name) or winner or first criteria key;
        winner gets prob `peak`, the rest share (1-peak) equally. Score answers: level `score_level`.
        score_shape: "float" (DEFAULT = the real live jev-1.13.0 shape: {"score": 2.0, "legend": {"0": text,..},
        "probabilities": {"0": p,..}}); "index" -> {"score": <int level>, ...}; "text" -> {"score": "<level text>"}.
        Probabilities keys are level indexes as strings in all shapes. See jev_client.SCORE_SHAPE_NOTE.
free_port() -> int
write_fake_claude(directory, behavior="valid", winner=None) -> path
    behavior: "valid" | "malformed_then_valid" | "always_malformed" | "exit_nonzero"
    The fake prints the `claude -p --output-format json` envelope; `result` is a JSON answers object built
    from the questions in its stdin prompt (first choice key, or `winner` if in criteria; score = middle level).
    Every invocation appends {"argv","skill_route_child","plugin_dirs","max_thinking_tokens","anthropic_key_set","stdin_len","prompt"} to <path>.record.jsonl.
set_fake_behavior(path, behavior, winner=None)   switch behaviour at runtime and reset its call counter
fake_claude_records(path) -> [dict]              invocations so far ([] if never invoked)
jev_test_env(stub=True, claude_behavior="valid", endpoint=None, extra_env=None, key=BOGUS_KEY,
             stub_mode="ok", **stub_kwargs) -> context manager yielding a JevEnv
"""
import contextlib
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
try:
    from socketserver import ThreadingMixIn
except ImportError:  # pragma: no cover
    from SocketServer import ThreadingMixIn

BOGUS_KEY = "bogus-test-key-NOT-REAL-0f1e2d3c4b5a"

_STATUS_MODES = ("400", "401", "403", "404", "408", "422", "429", "500", "502", "503", "504", "529")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --------------------------------------------------------------------------- stub server
class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class JevStub(object):
    def __init__(self, mode="ok", winner=None, winners=None, peak=0.8, score_level=2,
                 slow_seconds=4.0, score_shape="float", model="jev-stub"):
        self.mode = mode
        self.winner = winner
        self.winners = dict(winners or {})
        self.peak = peak
        self.score_level = score_level
        self.slow_seconds = slow_seconds
        self.score_shape = score_shape
        self.model = model
        self._lock = threading.Lock()
        self._count = 0
        self.requests = []
        self._server = None
        self._thread = None
        self.port = None

    # ---- lifecycle
    def start(self):
        stub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *a, **k):  # silence
                pass

            def _send(self, status, body, ctype="application/json"):
                try:
                    data = body if isinstance(body, bytes) else body.encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (OSError, ValueError):
                    pass  # client gave up (timeout test)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n).decode("utf-8", "replace") if n else ""
                try:
                    parsed = json.loads(raw)
                except ValueError:
                    parsed = None
                with stub._lock:
                    stub._count += 1
                    mode = stub.mode
                    stub.requests.append({"path": self.path, "headers": dict(self.headers.items()),
                                          "body": raw, "json": parsed, "mode": mode})
                if mode in _STATUS_MODES or (mode.isdigit() and mode != "200"):
                    self._send(int(mode), json.dumps({"error": "stub %s" % mode}))
                elif mode == "garbage":
                    self._send(200, "<html>not json at all", "text/html")
                elif mode == "badshape":
                    self._send(200, json.dumps({"hello": "world"}))
                else:
                    if mode == "slow":
                        time.sleep(stub.slow_seconds)
                    self._send(200, json.dumps(stub._build_ok(parsed)))

            do_GET = do_POST

        self._server = _Server(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05})
        self._thread.daemon = True
        self._thread.start()
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # ---- state
    @property
    def url(self):
        return "http://127.0.0.1:%d/v1/systemone" % self.port

    def set_mode(self, mode):
        self.mode = str(mode)

    @property
    def count(self):
        with self._lock:
            return self._count

    def reset(self):
        with self._lock:
            self._count = 0
            self.requests = []

    @property
    def last_body(self):
        with self._lock:
            return self.requests[-1]["json"] if self.requests else None

    @property
    def last_raw(self):
        with self._lock:
            return self.requests[-1]["body"] if self.requests else None

    @property
    def last_auth(self):
        with self._lock:
            if not self.requests:
                return None
            h = self.requests[-1]["headers"]
            for k, v in h.items():
                if k.lower() == "authorization":
                    return v
            return None

    # ---- ok-mode answer builder
    def _build_ok(self, body):
        questions = (body or {}).get("questions") or {}
        answers = {}
        in_chars = len((body or {}).get("state") or "") + len(json.dumps(questions))
        for name, q in questions.items():
            qtype = q.get("type")
            crit = q.get("criteria")
            if qtype == "choice" and isinstance(crit, dict) and crit:
                keys = list(crit.keys())
                win = self.winners.get(name) or self.winner
                if win not in keys:
                    win = keys[0]
                rest = [k for k in keys if k != win]
                probs = {}
                if rest:
                    probs[win] = self.peak
                    for k in rest:
                        probs[k] = (1.0 - self.peak) / len(rest)
                else:
                    probs[win] = 1.0
                answers[name] = {"type": "choice", "choice": win, "confidence": probs[win],
                                 "probabilities": probs}
            elif qtype == "score" and isinstance(crit, list) and crit:
                n = len(crit)
                lvl = min(max(int(self.score_level), 0), n - 1)
                probs = {}
                for i in range(n):
                    probs[str(i)] = 0.6 if i == lvl else 0.4 / max(n - 1, 1)
                val = crit[lvl] if self.score_shape == "text" else (
                    lvl if self.score_shape == "index" else float(lvl))
                answers[name] = {"type": "score", "score": val, "confidence": probs[str(lvl)],
                                 "legend": dict((str(i), c) for i, c in enumerate(crit)),
                                 "probabilities": probs}
            else:
                answers[name] = {"type": qtype or "noul", "confidence": 0.5, "probabilities": {}}
        return {"model": self.model, "answers": answers,
                "usage": {"input_tokens": max(in_chars // 4, 1), "output_tokens": 0}}


# --------------------------------------------------------------------------- fake claude
_FAKE_CLAUDE_SRC = r'''#!%(python)s
import json, os, sys
me = os.path.abspath(__file__)
cfg = {}
try:
    cfg = json.load(open(me + ".cfg"))
except Exception:
    pass
prompt = sys.stdin.read()
n = 0
try:
    n = int(open(me + ".count").read() or 0)
except Exception:
    pass
n += 1
open(me + ".count", "w").write(str(n))
with open(me + ".record.jsonl", "a") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:], "skill_route_child": os.environ.get("SKILL_ROUTE_CHILD"),
                         "plugin_dirs": os.environ.get("CLAUDE_CODE_PLUGIN_DIRS"),
                         "max_thinking_tokens": os.environ.get("MAX_THINKING_TOKENS"),
                         "anthropic_key_set": "ANTHROPIC_API_KEY" in os.environ,
                         "stdin_len": len(prompt), "prompt": prompt}) + "\n")
behavior = cfg.get("behavior", "valid")
winner = cfg.get("winner")
if behavior == "exit_nonzero":
    sys.stderr.write("fake claude: failing on purpose\n")
    sys.exit(3)
def answers_for(p):
    head = p.split("\n\nYour previous reply")[0]
    q = json.loads(head).get("questions", {})
    out = {}
    for name, spec in q.items():
        t = spec.get("type")
        c = spec.get("criteria")
        if t == "choice" and isinstance(c, dict) and c:
            keys = list(c.keys())
            w = winner if winner in keys else keys[0]
            rest = [k for k in keys if k != w]
            probs = {w: 0.7 if rest else 1.0}
            for k in rest[:2]:
                probs[k] = 0.3 / min(len(rest), 2)
            out[name] = {"choice": w, "confidence": probs[w], "probabilities": probs}
        elif t == "score" and isinstance(c, list) and c:
            lvl = len(c) // 2
            probs = dict((str(i), 0.6 if i == lvl else 0.4 / max(len(c) - 1, 1)) for i in range(len(c)))
            out[name] = {"score": lvl, "confidence": 0.6, "probabilities": probs}
        else:
            out[name] = {"noul": 0.5, "confidence": 0.5}
    return out
if behavior == "always_malformed" or (behavior == "malformed_then_valid" and n == 1):
    result = "Sure! I think the answer is probably the first option."
else:
    result = json.dumps(answers_for(prompt))
env = {"type": "result", "subtype": "success", "is_error": False, "result": result,
       "usage": {"input_tokens": 400, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                 "output_tokens": 60},
       "modelUsage": {"claude-haiku-fake": {"inputTokens": 400, "outputTokens": 60}},
       "total_cost_usd": 0.0005}
sys.stdout.write(json.dumps(env))
'''


def set_fake_behavior(path, behavior, winner=None):
    with open(path + ".cfg", "w") as fh:
        json.dump({"behavior": behavior, "winner": winner}, fh)
    try:
        os.remove(path + ".count")
    except OSError:
        pass


def write_fake_claude(directory, behavior="valid", winner=None):
    path = os.path.join(directory, "fake-claude")
    with open(path, "w") as fh:
        fh.write(_FAKE_CLAUDE_SRC % {"python": sys.executable})
    os.chmod(path, 0o755)
    set_fake_behavior(path, behavior, winner)
    try:
        os.remove(path + ".record.jsonl")
    except OSError:
        pass
    return path


def fake_claude_records(path):
    out = []
    try:
        with open(path + ".record.jsonl") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


# --------------------------------------------------------------------------- test env
_ENV_TOUCHED = ("AGENCY_SKILL_ROUTER", "AGENCY_HOME", "CLAUDE_CONFIG_DIR", "SKILL_ROUTE_STATE_DIR", "JEV_USAGE_LOG", "JEV_NOTIFY_LOG", "JEV_ENV_FILE", "JEV_ENDPOINT",
                "JEV_NOTIFY", "JEV_EMIT", "JEV_HAIKU_CMD", "JEV_PURPOSE", "JEV_MODEL", "SKILL_ROUTE_CHILD",
                "JEV_APPROVED_USD", "JEV_RUN_ID", "JEV_RUN_OWNER_PID", "JEV_RUN_STARTED_PPID", "JEV_CREDIT_FILE",
                "JEV_BUDGET_RESERVE_USD")


class JevEnv(object):
    def __init__(self, root):
        self.root = root
        self.state_dir = os.path.join(root, "state")
        self.usage_log = os.path.join(root, "logs", "jev-usage.jsonl")
        self.notify_log = os.path.join(root, "logs", "jev-notify.log")
        self.env_file = os.path.join(root, "typesafe.env")
        self.flag = os.path.join(self.state_dir, "jev-down")
        self.stub = None
        self.fake_claude = None

    def usage_records(self):
        return _read_jsonl(self.usage_log)

    def notify_lines(self, kind=None):
        try:
            with open(self.notify_log) as fh:
                lines = [l.rstrip("\n") for l in fh if l.strip()]
        except OSError:
            return []
        if kind:
            lines = [l for l in lines if l.split("\t")[-1] == kind]
        return lines

    def flag_exists(self):
        return os.path.exists(self.flag)

    def flag_info(self):
        try:
            with open(self.flag) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def write_env_file(self, key=BOGUS_KEY, model="jev-stub"):
        with open(self.env_file, "w") as fh:
            fh.write("TYPESAFE_API_KEY=%s\nJEV_MODEL=%s\n" % (key, model))


def _read_jsonl(path):
    out = []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


@contextlib.contextmanager
def jev_test_env(stub=True, claude_behavior="valid", endpoint=None, extra_env=None, key=BOGUS_KEY,
                 stub_mode="ok", **stub_kwargs):
    root = tempfile.mkdtemp(prefix="jev-test-")
    saved = dict((k, os.environ.get(k)) for k in _ENV_TOUCHED)
    saved.update((k, os.environ.get(k)) for k in (extra_env or {}))
    env = JevEnv(root)
    try:
        os.makedirs(env.state_dir)
        os.makedirs(os.path.dirname(env.usage_log))
        env.write_env_file(key)
        if stub:
            env.stub = JevStub(mode=stub_mode, **stub_kwargs).start()
        env.fake_claude = write_fake_claude(root, claude_behavior)
        for k in ("JEV_PURPOSE", "JEV_MODEL", "SKILL_ROUTE_CHILD", "CLAUDE_CONFIG_DIR", "JEV_RUN_ID",
                  "JEV_RUN_OWNER_PID", "JEV_RUN_STARTED_PPID", "JEV_CREDIT_FILE", "JEV_BUDGET_RESERVE_USD"):
            os.environ.pop(k, None)
        os.environ["JEV_APPROVED_USD"] = "1000"      # tests are pre-approved; the budget tests clear it
        os.environ.update({
            "AGENCY_SKILL_ROUTER": "1",      # the router ships disabled; a test that needs it off sets None in extra_env
            "AGENCY_HOME": root,             # any default-root fallback lands in the temp dir, never a real install
            "SKILL_ROUTE_STATE_DIR": env.state_dir,
            "JEV_USAGE_LOG": env.usage_log,
            "JEV_NOTIFY_LOG": env.notify_log,
            "JEV_ENV_FILE": env.env_file,
            "JEV_ENDPOINT": endpoint or (env.stub.url if env.stub else "http://127.0.0.1:9/v1/systemone"),
            "JEV_NOTIFY": "0",
            "JEV_EMIT": "0",
            "JEV_HAIKU_CMD": env.fake_claude,
        })
        for k, v in (extra_env or {}).items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield env
    finally:
        if env.stub is not None:
            env.stub.stop()
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(root, ignore_errors=True)
