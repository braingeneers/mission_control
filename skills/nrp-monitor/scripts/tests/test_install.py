"""install.sh runs end to end into a throwaway HOME (no launchd, no network)."""
import os, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def install(home, **extra):
    env = dict(os.environ, HOME=home, NRP_WATCHDOG_SETUP="skip", **extra)
    return subprocess.run(["sh", str(HERE / "install.sh")], env=env, capture_output=True, text=True)


class Install(unittest.TestCase):
    def test_installs_all_programs_into_a_fresh_home(self):
        with tempfile.TemporaryDirectory() as home:
            r = install(home, NRP_WATCHDOG_LABEL="test.nrp-watchdog")
            self.assertEqual(r.returncode, 0, r.stderr)
            for f in ("nrp-monitor", "nrp-watchdog", "nrp-util-check", "nrp-task", "nrp-s3-read"):
                self.assertTrue(os.access(Path(home, ".local/bin", f), os.X_OK), f)
            self.assertTrue(Path(home, "Library/LaunchAgents/test.nrp-watchdog.plist").exists())
            self.assertIn("config.json is missing", r.stdout)

    def test_nrp_watchdog_is_a_copy_wrapper_that_runs_nrp_monitor(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(install(home).returncode, 0)
            alias = Path(home, ".local/bin/nrp-watchdog")
            self.assertFalse(alias.is_symlink(), "launchd cannot read ~/Desktop: copy, never symlink")
            self.assertIn("nrp-monitor", alias.read_text())
            self.assertFalse(Path(home, ".local/bin/nrp-monitor").is_symlink())
            env = dict(os.environ, HOME=home, NRP_WATCHDOG_STATE=str(Path(home, "st")))
            for cmd in ("nrp-monitor", "nrp-watchdog"):
                r = subprocess.run([str(Path(home, ".local/bin", cmd)), "--help"], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, (cmd, r.stderr))
                self.assertIn("nrp-monitor", r.stdout + r.stderr)
            self.assertIn("nrp-monitor", Path(home, ".local/bin/nrp-task").read_text())

    def test_state_dir_and_launchd_label_keep_their_old_names(self):
        with tempfile.TemporaryDirectory() as home:
            user = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
            r = install(home)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(Path(home, ".local/state/nrp-watchdog/INSTALLED").exists())
            self.assertTrue(Path(home, ".local/state/nrp-watchdog/templates").is_dir())
            self.assertFalse(Path(home, ".local/state/nrp-monitor").exists())
            plist = Path(home, "Library/LaunchAgents/edu.ucsc.%s.nrp-watchdog.plist" % user)
            self.assertTrue(plist.exists(), "default label/plist name unchanged")
            text = plist.read_text()
            self.assertIn("edu.ucsc.%s.nrp-watchdog" % user, text)
            self.assertIn("%s/.local/bin/nrp-monitor</string>" % home, text, "the loaded agent now runs nrp-monitor")
            self.assertIn("%s/.local/state/nrp-watchdog" % home, text)


if __name__ == "__main__":
    unittest.main()
