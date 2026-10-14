"""Tests for scripts/skill-route-overlay-add.py.

All tests run on temp copies of the shipped overlay; the shipped file is never written.
"""
import difflib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
HELPER = os.path.join(SCRIPTS, "skill-route-overlay-add.py")
SHIPPED_OVERLAY = os.path.join(SCRIPTS, "skill-route", "overlay.json")


def load_helper():
    spec = importlib.util.spec_from_file_location("skill_route_overlay_add", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="overlay-add-test-")
        self.overlay = os.path.join(self.tmp, "overlay.json")
        shutil.copyfile(SHIPPED_OVERLAY, self.overlay)
        # the helper's lock file lives in the state dir: keep it out of a real install
        self.state = tempfile.mkdtemp(prefix="overlay-add-state-")
        self._old_state = os.environ.get("SKILL_ROUTE_STATE_DIR")
        os.environ["SKILL_ROUTE_STATE_DIR"] = self.state
        self.mod = load_helper()

    def tearDown(self):
        if self._old_state is None:
            os.environ.pop("SKILL_ROUTE_STATE_DIR", None)
        else:
            os.environ["SKILL_ROUTE_STATE_DIR"] = self._old_state
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.state, ignore_errors=True)

    def data(self):
        with open(self.overlay, encoding="utf-8") as f:
            return json.load(f)

    def cli(self, *args, overlay=None):
        env = dict(os.environ)
        env["SKILL_ROUTE_OVERLAY"] = overlay or self.overlay
        return subprocess.run([sys.executable, HELPER] + list(args), env=env,
                              capture_output=True, text=True)


class TestAddEntry(Base):
    def test_default_entry_added(self):
        status, entry = self.mod.add_entry("zz-new-skill", overlay_path=self.overlay)
        self.assertEqual(status, "added")
        self.assertEqual(entry["exclude"], "internal")
        self.assertIn("auto-added on install", entry["why"])
        self.assertIn("add domain+hint to make it routable", entry["why"])
        self.assertEqual(self.data()["skills"]["zz-new-skill"], entry)

    def test_exists_no_overwrite_byte_identical_mtime_untouched(self):
        existing = next(iter(self.data()["skills"]))
        os.utime(self.overlay, (1000000000, 1000000000))
        before = read_bytes(self.overlay)
        status, entry = self.mod.add_entry(existing, domain="research", hint="x",
                                           overlay_path=self.overlay)
        self.assertEqual(status, "exists")
        self.assertEqual(read_bytes(self.overlay), before)
        self.assertEqual(os.stat(self.overlay).st_mtime, 1000000000)

    def test_domain_entry_with_hint(self):
        status, entry = self.mod.add_entry("zz-routable", domain="research",
                                           hint="Use for X.", overlay_path=self.overlay)
        self.assertEqual(status, "added")
        self.assertEqual(entry, {"domain": "research", "hint": "Use for X."})
        self.assertEqual(self.data()["skills"]["zz-routable"], entry)

    def test_domain_without_hint_omits_key_and_why_only_if_given(self):
        _, e1 = self.mod.add_entry("zz-a", domain="research", overlay_path=self.overlay)
        self.assertEqual(e1, {"domain": "research"})
        _, e2 = self.mod.add_entry("zz-b", domain="research", hint="h", why="because",
                                   overlay_path=self.overlay)
        self.assertEqual(e2, {"domain": "research", "hint": "h", "why": "because"})

    def test_why_overrides_default(self):
        _, e = self.mod.add_entry("zz-w", why="custom why", overlay_path=self.overlay)
        self.assertEqual(e, {"exclude": "internal", "why": "custom why"})

    def test_unknown_domain_raises_file_untouched(self):
        before = read_bytes(self.overlay)
        with self.assertRaises(ValueError) as cm:
            self.mod.add_entry("zz-x", domain="nope", overlay_path=self.overlay)
        self.assertIn("research", str(cm.exception))  # lists valid domains
        self.assertEqual(read_bytes(self.overlay), before)

    def test_hint_without_domain_raises(self):
        before = read_bytes(self.overlay)
        with self.assertRaises(ValueError):
            self.mod.add_entry("zz-x", hint="h", overlay_path=self.overlay)
        self.assertEqual(read_bytes(self.overlay), before)

    def test_bad_names_raise(self):
        for bad in ["", "a/b", ".hidden", "_private", "  "]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.mod.add_entry(bad, overlay_path=self.overlay)

    def test_sorted_insertion_position(self):
        keys = list(self.data()["skills"])
        self.assertEqual(keys, sorted(keys))
        self.mod.add_entry("mmm-middle", overlay_path=self.overlay)
        self.mod.add_entry("0-first", overlay_path=self.overlay)
        self.mod.add_entry("zzzz-last", overlay_path=self.overlay)
        new_keys = list(self.data()["skills"])
        self.assertEqual(new_keys, sorted(new_keys))
        self.assertEqual(new_keys[0], "0-first")
        self.assertEqual(new_keys[-1], "zzzz-last")
        self.assertEqual(len(new_keys), len(keys) + 3)

    def test_unsorted_keys_append_at_end(self):
        d = self.data()
        d["skills"] = {"zeta": {"domain": "research"}, "alpha": {"domain": "research"}}
        with open(self.overlay, "w") as f:
            f.write(json.dumps(d, indent=1, ensure_ascii=True) + "\n")
        self.mod.add_entry("middle", overlay_path=self.overlay)
        self.assertEqual(list(self.data()["skills"]), ["zeta", "alpha", "middle"])

    def test_round_trip_formatting_only_new_lines_differ(self):
        before = read_bytes(self.overlay).decode("utf-8")
        self.mod.add_entry("mmm-middle", overlay_path=self.overlay)
        after = read_bytes(self.overlay).decode("utf-8")
        self.assertTrue(after.endswith("\n"))
        entry = self.data()["skills"]["mmm-middle"]
        # the entry lines exactly as they sit inside "skills" (indent=1 -> depth 2)
        expected = json.dumps({"skills": {"mmm-middle": entry}}, indent=1).splitlines()[2:-2]
        self.assertEqual(expected[0], '  "mmm-middle": {')
        # a comma moves between neighbours, so compare with trailing commas ignored
        strip = lambda ls: [l.rstrip(",") for l in ls]
        b_lines, a_lines = before.splitlines(), after.splitlines()
        start = a_lines.index(expected[0])
        end = start + len(expected)
        self.assertEqual(strip(a_lines[start:end]), strip(expected))
        # removing exactly the new entry lines gives back the original, up to commas
        kept = a_lines[:start] + a_lines[end:]
        self.assertEqual(strip(kept), strip(b_lines))
        # and the unified diff shows nothing but additions of those lines (plus comma moves)
        removed = [l[1:] for l in difflib.unified_diff(b_lines, a_lines, lineterm="", n=0)
                   if l.startswith("-") and not l.startswith("---")]
        # at most the previous neighbour line changes (comma moved onto it)
        self.assertLessEqual(len(removed), 1)

    def test_raw_non_ascii_preserved_when_present(self):
        d = self.data()
        d["notes"] = "café — test"
        with open(self.overlay, "w", encoding="utf-8") as f:
            f.write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
        self.mod.add_entry("zz-n", overlay_path=self.overlay)
        raw = read_bytes(self.overlay).decode("utf-8")
        self.assertIn("café — test", raw)

    def test_ascii_escapes_preserved_when_no_raw_non_ascii(self):
        escaped = json.dumps(self.data(), indent=1, ensure_ascii=True) + "\n"   # the shipped overlay holds raw UTF-8
        with open(self.overlay, "w", encoding="utf-8") as f:
            f.write(escaped)
        self.mod.add_entry("zz-n", overlay_path=self.overlay)
        raw = read_bytes(self.overlay)
        raw.decode("ascii")  # still pure ascii

    def test_no_trailing_newline_preserved(self):
        raw = read_bytes(self.overlay).rstrip(b"\n")
        with open(self.overlay, "wb") as f:
            f.write(raw)
        self.mod.add_entry("zz-n", overlay_path=self.overlay)
        self.assertFalse(read_bytes(self.overlay).endswith(b"\n"))

    def test_atomic_write_leaves_no_temp_files_and_keeps_mode(self):
        os.chmod(self.overlay, 0o640)
        self.mod.add_entry("zz-n", overlay_path=self.overlay)
        self.assertEqual(os.listdir(self.tmp), ["overlay.json"])
        self.assertEqual(stat.S_IMODE(os.stat(self.overlay).st_mode), 0o640)

    def test_invalid_overlay_raises_overlay_error(self):
        for content in ["not json", "[1,2]", '{"domains": {}}', '{"skills": []}']:
            with open(self.overlay, "w") as f:
                f.write(content)
            with self.assertRaises(self.mod.OverlayError, msg=content):
                self.mod.add_entry("zz-n", overlay_path=self.overlay)
        with self.assertRaises(self.mod.OverlayError):
            self.mod.add_entry("zz-n", overlay_path=os.path.join(self.tmp, "missing.json"))

    def test_env_overlay_path_default_rule(self):
        os.environ["SKILL_ROUTE_OVERLAY"] = self.overlay
        try:
            self.assertEqual(self.mod.overlay_path(), self.overlay)
        finally:
            del os.environ["SKILL_ROUTE_OVERLAY"]
        self.assertEqual(self.mod.overlay_path(),
                         os.path.join(SCRIPTS, "skill-route", "overlay.json"))


class TestCLI(Base):
    def test_add_default(self):
        r = self.cli("zz-cli")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("added: zz-cli", r.stdout)
        self.assertEqual(self.data()["skills"]["zz-cli"]["exclude"], "internal")

    def test_exists_exit0(self):
        existing = next(iter(self.data()["skills"]))
        before = read_bytes(self.overlay)
        r = self.cli(existing)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "exists: " + existing)
        self.assertEqual(read_bytes(self.overlay), before)

    def test_domain_and_hint(self):
        r = self.cli("zz-cli", "--domain", "research", "--hint", "Use for Y.")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.data()["skills"]["zz-cli"],
                         {"domain": "research", "hint": "Use for Y."})

    def test_unknown_domain_exit2(self):
        before = read_bytes(self.overlay)
        r = self.cli("zz-cli", "--domain", "nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("research", r.stderr)
        self.assertEqual(read_bytes(self.overlay), before)

    def test_hint_without_domain_exit2(self):
        before = read_bytes(self.overlay)
        r = self.cli("zz-cli", "--hint", "h")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(read_bytes(self.overlay), before)

    def test_bad_name_exit2(self):
        for bad in ["a/b", ".x", "_x"]:
            r = self.cli(bad)
            self.assertEqual(r.returncode, 2, bad)

    def test_invalid_overlay_exit1(self):
        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w") as f:
            f.write('{"domains": {}}')
        r = self.cli("zz-cli", overlay=bad)
        self.assertEqual(r.returncode, 1)
        r = self.cli("zz-cli", overlay=os.path.join(self.tmp, "missing.json"))
        self.assertEqual(r.returncode, 1)


class TestInvalidExistingEntry(Base):
    """An existing-but-broken entry is never overwritten, but it is reported (the menu build still fails on it)."""

    def put(self, entry):
        d = self.data()
        d["skills"]["zz-broken"] = entry
        with open(self.overlay, "w") as f:
            f.write(json.dumps(d, indent=1, ensure_ascii=True) + "\n")

    BAD = [
        (None, "not an object"),
        ("x", "not an object"),
        ([], "not an object"),
        ({}, "no 'exclude' or 'domain'"),
        ({"hint": "h"}, "no 'exclude' or 'domain'"),
        ({"exclude": "", "domain": ""}, "no 'exclude' or 'domain'"),
        ({"domain": "nope"}, "unknown domain"),
        ({"domain": "research", "also_domains": ["nope"]}, "unknown also_domains"),
    ]

    def test_invalid_shapes_return_invalid_untouched(self):
        for entry, why in self.BAD:
            self.put(entry)
            os.utime(self.overlay, (1000000000, 1000000000))
            before = read_bytes(self.overlay)
            status, got = self.mod.add_entry("zz-broken", domain="research", hint="x",
                                             overlay_path=self.overlay)
            self.assertEqual(status, "invalid", repr(entry))
            self.assertEqual(got, entry)
            self.assertEqual(read_bytes(self.overlay), before, repr(entry))
            self.assertEqual(os.stat(self.overlay).st_mtime, 1000000000)
            self.assertIn(why, self.mod.entry_problem(self.data()["skills"]["zz-broken"], self.data()["domains"]))

    def test_valid_shapes_still_exist(self):
        for entry in [{"exclude": "internal"},
                      {"domain": "research"},
                      {"domain": "research", "also_domains": ["research"]},
                      {"exclude": "x", "also_domains": ["nope"]}]:   # exclude returns before the also check in _build_menu
            self.put(entry)
            status, _ = self.mod.add_entry("zz-broken", overlay_path=self.overlay)
            self.assertEqual(status, "exists", repr(entry))

    def test_cli_invalid_entry_exit1_stderr_stdout_empty(self):
        self.put({})
        before = read_bytes(self.overlay)
        r = self.cli("zz-broken")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("exists (invalid entry: no 'exclude' or 'domain'): zz-broken", r.stderr)
        self.assertEqual(read_bytes(self.overlay), before)

    def test_cli_null_entry(self):
        self.put(None)
        r = self.cli("zz-broken")
        self.assertEqual(r.returncode, 1)
        self.assertIn("exists (invalid entry: not an object): zz-broken", r.stderr)

    def test_cli_valid_exists_still_exit0(self):
        existing = next(iter(self.data()["skills"]))
        r = self.cli(existing)
        self.assertEqual(r.returncode, 0)


class TestLocking(Base):
    def test_concurrent_adds_lose_nothing(self):
        n = 12
        env = dict(os.environ, SKILL_ROUTE_OVERLAY=self.overlay)
        before = len(self.data()["skills"])
        procs = [subprocess.Popen([sys.executable, HELPER, "zz-par-%02d" % i], env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                 for i in range(n)]
        for p in procs:
            out, err = p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0, err)
        skills = self.data()["skills"]          # valid JSON or this raises
        self.assertEqual(len(skills), before + n)
        for i in range(n):
            self.assertIn("zz-par-%02d" % i, skills)
        self.assertEqual(list(skills), sorted(skills))

    def test_lock_file_in_state_dir_not_next_to_overlay(self):
        self.mod.add_entry("zz-n", overlay_path=self.overlay)
        self.assertEqual(os.listdir(self.tmp), ["overlay.json"])
        locks = [f for f in os.listdir(self.state) if f.endswith(".lock")]
        self.assertEqual(len(locks), 1, os.listdir(self.state))
        self.mod.add_entry("zz-m", overlay_path=self.overlay)     # reused, never deleted
        self.assertEqual([f for f in os.listdir(self.state) if f.endswith(".lock")], locks)

    def test_lock_name_differs_per_overlay(self):
        other = os.path.join(self.tmp, "other.json")
        shutil.copyfile(self.overlay, other)
        self.mod.add_entry("zz-a", overlay_path=self.overlay)
        self.mod.add_entry("zz-a", overlay_path=other)
        self.assertEqual(len([f for f in os.listdir(self.state) if f.endswith(".lock")]), 2)

    def test_unusable_state_dir_falls_back_to_tempdir(self):
        blocker = os.path.join(self.tmp, "afile")
        with open(blocker, "w") as f:
            f.write("x")
        os.environ["SKILL_ROUTE_STATE_DIR"] = os.path.join(blocker, "state")   # cannot be created
        tdir = tempfile.mkdtemp(prefix="overlay-add-tmpdir-")
        old = tempfile.tempdir
        tempfile.tempdir = tdir
        try:
            status, _ = self.mod.add_entry("zz-fb", overlay_path=self.overlay)
        finally:
            tempfile.tempdir = old
        self.assertEqual(status, "added")
        self.assertEqual(len([f for f in os.listdir(tdir) if f.endswith(".lock")]), 1)
        shutil.rmtree(tdir, ignore_errors=True)

    def test_no_lock_possible_proceeds_with_stderr_warning(self):
        blocker = os.path.join(self.tmp, "afile")
        with open(blocker, "w") as f:
            f.write("x")
        os.environ["SKILL_ROUTE_STATE_DIR"] = os.path.join(blocker, "state")
        old = tempfile.tempdir
        tempfile.tempdir = os.path.join(blocker, "tmp")
        old_err, sys.stderr = sys.stderr, io.StringIO()
        try:
            status, _ = self.mod.add_entry("zz-nolock", overlay_path=self.overlay)
            warn = sys.stderr.getvalue()
        finally:
            sys.stderr = old_err
            tempfile.tempdir = old
        self.assertEqual(status, "added")
        self.assertIn("zz-nolock", self.data()["skills"])
        self.assertIn("without a lock", warn)


class TestSymlinkedOverlay(Base):
    def test_symlink_survives_and_target_is_updated(self):
        real_dir = os.path.join(self.tmp, "real")
        os.makedirs(real_dir)
        real = os.path.join(real_dir, "overlay.json")
        os.replace(self.overlay, real)
        os.chmod(real, 0o640)
        link = os.path.join(self.tmp, "link.json")
        os.symlink(real, link)
        status, _ = self.mod.add_entry("zz-sym", overlay_path=link)
        self.assertEqual(status, "added")
        self.assertTrue(os.path.islink(link))
        self.assertEqual(os.path.realpath(link), os.path.realpath(real))
        with open(real) as f:
            self.assertIn("zz-sym", json.load(f)["skills"])
        self.assertEqual(stat.S_IMODE(os.stat(real).st_mode), 0o640)
        self.assertEqual(os.listdir(real_dir), ["overlay.json"])

    def test_cli_symlink(self):
        real = os.path.join(self.tmp, "real.json")
        os.replace(self.overlay, real)
        link = os.path.join(self.tmp, "overlay.json")
        os.symlink(real, link)
        r = self.cli("zz-sym2", overlay=link)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.islink(link))
        with open(real) as f:
            self.assertIn("zz-sym2", json.load(f)["skills"])


if __name__ == "__main__":
    unittest.main()
