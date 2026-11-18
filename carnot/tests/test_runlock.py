"""Run lock: a second holder is refused while the first is alive."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from carnot import common


class RunLockTest(unittest.TestCase):
    def test_second_lock_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".run.lock"
            first = common.RunLock(path, "first")
            with self.assertRaises(common.LockHeld) as caught:
                common.RunLock(path, "second")
            self.assertIn("first", str(caught.exception))
            first.handle.close()
            common.RunLock(path, "third").handle.close()


if __name__ == "__main__":
    unittest.main()
