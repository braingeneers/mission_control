"""install.sh runs end to end into a throwaway HOME (no launchd, no network)."""
import os, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


class Install(unittest.TestCase):
    def test_installs_all_programs_into_a_fresh_home(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, NRP_WATCHDOG_LABEL="test.nrp-watchdog")
            r = subprocess.run(["sh", str(HERE / "install.sh")], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            for f in ("nrp-watchdog", "nrp-util-check", "nrp-task", "nrp-s3-read"):
                self.assertTrue(os.access(Path(home, ".local/bin", f), os.X_OK), f)
            self.assertTrue(Path(home, "Library/LaunchAgents/test.nrp-watchdog.plist").exists())
            self.assertIn("config.json is missing", r.stdout)


if __name__ == "__main__":
    unittest.main()
