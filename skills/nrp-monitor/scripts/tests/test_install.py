"""install.sh runs end to end into a throwaway HOME (no launchd, no network)."""
import os, subprocess, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def install(home, **extra):
    fake_bin = Path(home, "fake-bin")
    fake_bin.mkdir(exist_ok=True)
    launchctl = fake_bin / "launchctl"
    launchctl.write_text('#!/bin/sh\n[ "$1" = print ] && exit 1\nexit 0\n')
    launchctl.chmod(0o755)
    env = dict(os.environ, HOME=home, NRP_MONITOR_SETUP="skip", **extra)
    env["PATH"] = str(fake_bin) + os.pathsep + os.environ["PATH"]
    return subprocess.run(["sh", str(HERE / "install.sh")], env=env, capture_output=True, text=True)


class Install(unittest.TestCase):
    def test_installs_all_programs_into_a_fresh_home(self):
        with tempfile.TemporaryDirectory() as home:
            r = install(home, NRP_MONITOR_LABEL="test.nrp-monitor")
            self.assertEqual(r.returncode, 0, r.stderr)
            for f in ("nrp-monitor", "nrp-watchdog", "nrp-util-check", "nrp-task", "nrp-s3-read"):
                self.assertTrue(os.access(Path(home, ".local/bin", f), os.X_OK), f)
            self.assertTrue(Path(home, "Library/LaunchAgents/test.nrp-monitor.plist").exists())
            self.assertIn("config.json is missing", r.stdout)

    def test_nrp_monitor_is_a_copy_wrapper_that_runs_nrp_monitor(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(install(home).returncode, 0)
            alias = Path(home, ".local/bin/nrp-watchdog")
            self.assertFalse(alias.is_symlink(), "launchd cannot read ~/Desktop: copy, never symlink")
            self.assertIn("nrp-monitor", alias.read_text())
            self.assertFalse(Path(home, ".local/bin/nrp-monitor").is_symlink())
            env = dict(os.environ, HOME=home, NRP_MONITOR_STATE=str(Path(home, "st")))
            for cmd in ("nrp-monitor", "nrp-watchdog"):
                r = subprocess.run([str(Path(home, ".local/bin", cmd)), "--help"], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, (cmd, r.stderr))
                self.assertIn("nrp-monitor", r.stdout + r.stderr)
            self.assertIn("nrp-monitor", Path(home, ".local/bin/nrp-task").read_text())

    def test_legacy_environment_is_silent_and_new_values_win(self):
        import sys
        with tempfile.TemporaryDirectory() as home:
            for primary in (False, True):
                env = {k: v for k, v in os.environ.items() if not k.startswith(("NRP_MONITOR_", "NRP_WATCHDOG_"))}
                env.update(HOME=home, NRP_WATCHDOG_STATE=home+"/old")
                if primary:
                    env["NRP_MONITOR_STATE"] = home+"/new"
                code = "import runpy; print(runpy.run_path(%r)['STATE'])" % str(HERE/'nrp-monitor')
                r = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), home+("/new" if primary else "/old"))
                self.assertEqual(r.stderr, '')

    def test_fresh_state_dir_and_launchd_label_use_new_name(self):
        with tempfile.TemporaryDirectory() as home:
            user = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
            r = install(home)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(Path(home, ".local/state/nrp-monitor/INSTALLED").exists())
            self.assertTrue(Path(home, ".local/state/nrp-monitor/templates").is_dir())
            self.assertFalse(Path(home, ".local/state/nrp-watchdog").exists())
            plist = Path(home, "Library/LaunchAgents/edu.ucsc.%s.nrp-monitor.plist" % user)
            self.assertTrue(plist.exists(), "new default label/plist")
            text = plist.read_text()
            self.assertIn("edu.ucsc.%s.nrp-monitor" % user, text)
            self.assertIn("%s/.local/bin/nrp-monitor</string>" % home, text, "the loaded agent now runs nrp-monitor")
            self.assertIn("%s/.local/state/nrp-monitor" % home, text)


if __name__ == "__main__":
    unittest.main()

class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.old = self.home / '.local/state/nrp-watchdog'
        self.new = self.home / '.local/state/nrp-monitor'
        self.old.mkdir(parents=True)
        self.user = subprocess.check_output(['id', '-un'], text=True).strip()
        self.label = 'edu.ucsc.%s.nrp-watchdog' % self.user
        self.plist = self.home / ('Library/LaunchAgents/' + self.label + '.plist')
        self.plist.parent.mkdir(parents=True)
        self.plist.write_text('old plist')
        self.bin = self.home / 'fake-bin'
        self.bin.mkdir()
        fake = self.bin / 'launchctl'
        fake.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
home = Path(os.environ['HOME'])
a = sys.argv[1:]
with (home / 'launchctl.log').open('a') as f: f.write(' '.join(a) + '\\n')
loaded = home / 'loaded'
if a[0] == 'print': sys.exit(0 if loaded.exists() and loaded.read_text() in a[1] else 1)
if a[0] == 'bootout':
    if loaded.exists() and loaded.read_text() in a[1]: loaded.write_text('unloaded')
if a[0] == 'bootstrap': loaded.write_text(Path(a[2]).stem)
''')
        fake.chmod(0o755)

    def run_install(self, *args):
        env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin)+os.pathsep+os.environ['PATH'],
                   NRP_MONITOR_SETUP='skip', NRP_MONITOR_MIGRATE_WAIT='0')
        env.pop('NRP_MONITOR_LABEL', None)
        env.pop('NRP_WATCHDOG_LABEL', None)
        return subprocess.run(['sh', str(HERE/'install.sh'), *args], env=env, capture_output=True, text=True)

    def test_migration_moves_rewrites_swaps_loaded_label_and_is_idempotent(self):
        import json
        (self.home/'loaded').write_text(self.label)
        for d in ('tasks/t1', 'plans/p1', 'chains/c1'):
            p = self.old/d/'state.json'; p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'path': str(self.old/d), 'nested': [str(self.old)],
                                     'prose': 'look '+str(self.old), 'other': str(self.old)+'-other'}))
        (self.old/'watchdog.log').write_text('saved logs')
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.old.is_symlink())
        self.assertEqual(self.old.resolve(), self.new.resolve())
        for d in ('tasks/t1', 'plans/p1', 'chains/c1'):
            state = json.loads((self.new/d/'state.json').read_text())
            self.assertEqual(state['path'], str(self.new/d))
            self.assertEqual(state['nested'], [str(self.new)])
            self.assertEqual(state['prose'], 'look '+str(self.old))
            self.assertEqual(state['other'], str(self.old)+'-other')
        self.assertFalse(self.plist.exists())
        self.assertEqual((self.new/'monitor.log').read_text(), 'saved logs')
        self.assertEqual((self.home/'loaded').read_text(), self.label.replace('watchdog','monitor'))
        calls = (self.home/'launchctl.log').read_text()
        self.assertLess(calls.index('bootout'), calls.index('bootstrap'))
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('migration:', r.stdout)
        self.assertEqual((self.home/'launchctl.log').read_text().count('bootstrap'), 1)

    def test_refuses_locked_state_and_reloads_old_scheduler(self):
        import fcntl
        (self.home/'loaded').write_text(self.label)
        with (self.old/'lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            r = self.run_install()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('still held', r.stderr)
        self.assertTrue(self.old.is_dir())
        self.assertFalse(self.old.is_symlink())
        self.assertFalse(self.new.exists())
        # monitoring must not silently stop: the old label is loaded again (when its plist exists)
        self.assertEqual((self.home/'loaded').read_text(), self.label)
        self.assertIn('reloaded', r.stderr)

    def test_unloaded_migration_does_not_load_without_flag(self):
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('bootstrap', (self.home/'launchctl.log').read_text())

    def test_launchd_flag_loads_new_label(self):
        r = self.run_install('--launchd')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.home/'loaded').read_text(), self.label.replace('watchdog','monitor'))
