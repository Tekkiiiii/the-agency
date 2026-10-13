"""mods/_shared/platform.ts is the canonical helper; each mod ships a byte-identical copy
(a mod cannot import outside its own plugin folder, and symlinks pointing out are refused).
Run from the repo root: python3 mods/_shared/test_copies_identical.py
"""
import pathlib
import unittest

MODS = pathlib.Path(__file__).resolve().parent.parent
CANON = pathlib.Path(__file__).resolve().parent / "platform.ts"


class CopiesIdentical(unittest.TestCase):
    def test_each_mod_copy_matches_canonical(self):
        canon = CANON.read_bytes()
        for mod in ("agent-ctx", "context-band", "loop-guard", "spawn-ledger"):
            with self.subTest(mod=mod):
                copy = MODS / mod / "hooks" / "platform.ts"
                self.assertTrue(copy.is_file(), f"{copy} missing: cp _shared/platform.ts {mod}/hooks/")
                self.assertEqual(copy.read_bytes(), canon, f"{mod}/hooks/platform.ts differs from _shared/platform.ts: re-copy")

    def test_copy_banner_is_first_line(self):
        first = CANON.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(first.startswith("// COPY of mods/_shared/platform.ts"))


if __name__ == "__main__":
    unittest.main()
