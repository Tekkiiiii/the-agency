"""Higgsfield fence agent files: agents/general-purpose.md (fenced) overrides the built-in; agents/general-purpose-media.md is the unfenced twin.

Paths resolve from the repo root, so the test reads the shipped files, never an installed copy."""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FENCED = ROOT / "agents/general-purpose.md"
MEDIA = ROOT / "agents/general-purpose-media.md"
MODEL_PIN = ROOT / "hooks/lib/model-pin.py"


def parse(p):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", p.read_text(encoding="utf-8"), re.S)
    assert m, f"{p} has no frontmatter"
    return m.group(1), m.group(2)


class GpFence(unittest.TestCase):
    def test_fenced_frontmatter(self):
        fm, _ = parse(FENCED)
        self.assertTrue(re.search(r"^name: general-purpose$", fm, re.M))
        self.assertTrue(re.search(r"^disallowedTools: mcp__claude_ai_Higgsfield$", fm, re.M))
        self.assertFalse(re.search(r"^(model|tools|mcpServers):", fm, re.M))

    def test_fenced_body_is_the_exec_prompt(self):
        body = parse(FENCED)[1]
        self.assertIn("You are an agent for Claude Code", body)
        self.assertIn("do not re-delegate your entire assignment", body)

    def test_media_unfenced_same_body(self):
        fm, body = parse(MEDIA)
        self.assertTrue(re.search(r"^name: general-purpose-media$", fm, re.M))
        self.assertNotIn("disallowedTools", fm)
        self.assertFalse(re.search(r"^(model|tools|mcpServers):", fm, re.M))
        self.assertTrue(re.search(r"spawn-ledger", fm))
        self.assertEqual(body.strip(), parse(FENCED)[1].strip())

    def test_pin_sees_original_type_not_media(self):
        """The pin/cap key on the ORIGINAL type (the rewrite happens after); the media type never needs a pin entry."""
        spec = importlib.util.spec_from_file_location("model_pin", MODEL_PIN)
        mp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mp)
        self.assertIn("general-purpose", mp.GP_TYPES)
        self.assertEqual(mp.norm_type("general-purpose"), "general-purpose")
        self.assertEqual(mp.norm_type("general-purpose-media"), "general-purpose-media")


if __name__ == "__main__":
    unittest.main()
