import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import memory_ops


class MemoryOpsTests(unittest.TestCase):
    def test_structured_memory_migrates_old_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_file = Path(tmpdir) / "memory.json"
            memory_file.write_text('["My name is Deb"]', encoding="utf-8")

            with patch.object(memory_ops, "MEMORY_FILE", memory_file):
                memory_ops.remember_fact("I prefer concise answers")
                retrieved = memory_ops.retrieve_facts()

        self.assertIn("Facts: My name is Deb", retrieved)
        self.assertIn("Preferences: I prefer concise answers", retrieved)


if __name__ == "__main__":
    unittest.main()
