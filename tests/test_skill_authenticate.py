"""Offline sign-in tests. Only synthetic credentials and temporary directories."""

import base64
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import select
import signal
import stat
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SKILL = next(path for path in (
    ROOT / "skills/mission-control-services-management",
    ROOT / "skills/data-explorer-cli-access",
) if path.is_dir())
SCRIPT = SKILL / "scripts/authenticate.py"
spec = importlib.util.spec_from_file_location("skill_authenticate", SCRIPT)
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


def response(exp=None):
    payload = base64.urlsafe_b64encode(json.dumps({
        "exp": time.time() + 86400 * 30 if exp is None else exp,
        "test": "synthetic-only",
    }).encode()).decode().rstrip("=")
    return json.dumps({"access_token": "header." + payload + ".SYNTHETIC_SIGNATURE",
                       "expires_at": "2099-01-01T00:00:00Z"})


class SignInTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.path = self.home / ".ssh/braingeneers_jwt_token.json"
        self.raw = response()
        self.output = io.StringIO()
        self.addCleanup(patch.stopall)
        patch.object(auth.Path, "home", return_value=self.home).start()
        patch.object(auth.importlib, "import_module", side_effect=ImportError).start()

    def run_main(self, args):
        with redirect_stdout(self.output), redirect_stderr(self.output):
            return auth.main(args)

    def test_discovery_default_explicit_and_installed_package(self):
        self.assertEqual(auth.select_path(), self.path)
        self.assertEqual(auth.select_path(self.home / "chosen.json"), self.home / "chosen.json")
        package = self.home / "site-packages/braingeneers/iot"
        package_file = package / "service_account/config.json"
        package_file.parent.mkdir(parents=True)
        package_file.write_text(self.raw)
        with patch.object(auth.importlib, "import_module", return_value=SimpleNamespace(__path__=[str(package)])):
            self.assertEqual(auth.select_path(), package_file)
            # An existing but unusable preferred file is still the selected file.
            self.path.parent.mkdir()
            self.path.write_text("")
            self.assertEqual(auth.select_path(), self.path)
            self.assertEqual(auth.select_path(package_file), package_file)

    def test_valid_save_is_private_and_uses_embedded_expiry(self):
        expiry = auth.save_response(self.path, self.raw)
        self.assertEqual(json.loads(self.raw), json.loads(self.path.read_text()))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertLess(expiry.year, 2099)
        self.assertEqual(auth.check_response(self.path), expiry)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_reject_invalid_or_expired_without_replacing(self):
        auth.save_response(self.path, self.raw)
        for raw in ("<html>sign in</html>", "{}", "[]", response(time.time() - 5),
                    '{"access_token": "bad", "expires_at":"later"}',
                    response(True), response(float("nan")), response(1e100)):
            with self.subTest(raw=raw):
                with self.assertRaises(auth.SignInError):
                    auth.save_response(self.path, raw)
                self.assertEqual(json.loads(self.path.read_text()), json.loads(self.raw))

    def test_failed_atomic_replace_preserves_original_and_cleans_staging(self):
        auth.save_response(self.path, self.raw)
        with patch.object(auth.os, "replace", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                auth.save_response(self.path, response(time.time() + 90000))
        self.assertEqual(json.loads(self.path.read_text()), json.loads(self.raw))
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_import_same_file_secures_permissions(self):
        self.path.parent.mkdir()
        self.path.write_text(self.raw)
        self.path.chmod(0o644)
        self.assertEqual(self.run_main(["--check"]), 1)
        self.assertEqual(self.run_main(["--import-file", str(self.path)]), 0)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertNotIn(json.loads(self.raw)["access_token"], self.output.getvalue())

    def test_import_download_and_check_do_not_open_browser_or_claim_remote_access(self):
        download = self.home / "download.json"
        download.write_text(self.raw)
        with patch.object(auth.webbrowser, "open") as browser:
            self.assertEqual(self.run_main(["--import-file", str(download)]), 0)
            self.assertEqual(self.run_main(["--check"]), 0)
            browser.assert_not_called()
        self.assertIn("read-only", self.output.getvalue())
        self.assertNotIn("SYNTHETIC_SIGNATURE", self.output.getvalue())

    def test_noninteractive_fails_without_opening_browser_or_reading_input(self):
        with patch.object(auth.sys.stdin, "isatty", return_value=False), \
             patch.object(auth.webbrowser, "open") as browser:
            self.assertEqual(self.run_main([]), 1)
            browser.assert_not_called()
        self.assertFalse(self.path.exists())
        self.assertIn("own interactive terminal", self.output.getvalue())

    def test_browser_failure_keeps_link_and_private_prompt_available(self):
        with patch.object(auth.sys.stdin, "isatty", return_value=True), \
             patch.object(auth.webbrowser, "open", side_effect=OSError("no browser")), \
             patch.object(auth, "read_private_response", side_effect=lambda show: (show(), self.raw)[1]):
            self.assertEqual(self.run_main([]), 0)
        self.assertIn(auth.LOGIN_URL, self.output.getvalue())
        self.assertNotIn("SYNTHETIC_SIGNATURE", self.output.getvalue())

    def test_cancellation_and_sanitized_errors_preserve_file(self):
        auth.save_response(self.path, self.raw)
        with patch.object(auth.sys.stdin, "isatty", return_value=True), \
             patch.object(auth, "read_private_response", side_effect=KeyboardInterrupt):
            self.assertEqual(self.run_main(["--no-browser"]), 1)
        with patch.object(auth, "load_response", side_effect=OSError(self.raw)):
            self.assertEqual(self.run_main(["--check"]), 1)
        self.assertEqual(json.loads(self.path.read_text()), json.loads(self.raw))
        self.assertNotIn("SYNTHETIC_SIGNATURE", self.output.getvalue())

    def test_private_collector_multiline_and_cancellation(self):
        formatted = json.dumps(json.loads(self.raw), indent=2)
        chars = iter(formatted + "\n\n")
        self.assertEqual(json.loads(auth.collect_response(lambda: next(chars))), json.loads(self.raw))
        for char, error in (("\x03", KeyboardInterrupt), ("\x04", EOFError)):
            with self.assertRaises(error):
                auth.collect_response(lambda: char)

    def test_path_mode_never_reads_credential(self):
        with patch.object(auth, "load_response", side_effect=AssertionError("must not read")):
            self.assertEqual(self.run_main(["--path"]), 0)
        self.assertEqual(self.output.getvalue().strip(), str(self.path))

    @unittest.skipUnless(os.name == "posix", "POSIX terminal integration")
    def test_real_terminal_hides_long_multiline_paste_and_restores_echo(self):
        self.run_terminal_paste(delayed_browser=False)

    @unittest.skipUnless(os.name == "posix", "POSIX terminal integration")
    def test_paste_during_browser_startup_is_already_hidden(self):
        self.run_terminal_paste(delayed_browser=True)

    def run_terminal_paste(self, delayed_browser):
        import pty
        import termios

        # A long line verifies that canonical TTY input does not truncate JSON.
        data = json.loads(self.raw)
        data["padding"] = "x" * 6000
        formatted = json.dumps(data, indent=2)
        pid, master = pty.fork()
        if pid == 0:
            if delayed_browser:
                # Simulate browser startup while the user can already see the
                # paste invitation. No real browser or network is involved.
                def browser_startup(url):
                    print("SYNTHETIC_BROWSER_STARTING", flush=True)
                    time.sleep(0.3)
                    return True

                auth.webbrowser.open = browser_startup
                os._exit(auth.main(["--token-file", str(self.path)]))
            else:
                os.execv(sys.executable, [sys.executable, str(SCRIPT), "--no-browser",
                                         "--token-file", str(self.path)])
        output = bytearray()
        status = None
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if ((not delayed_browser and not termios.tcgetattr(master)[3] & termios.ECHO)
                        or (delayed_browser and b"SYNTHETIC_BROWSER_STARTING" in output)):
                    break
                if select.select([master], [], [], 0.05)[0]:
                    output.extend(os.read(master, 65536))
            else:
                self.fail("helper did not enable private terminal input")
            self.assertFalse(termios.tcgetattr(master)[3] & termios.ECHO)
            os.write(master, (formatted + "\n\n").encode())
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    try:
                        output.extend(os.read(master, 65536))
                    except OSError:
                        pass
                ended, status = os.waitpid(pid, os.WNOHANG)
                if ended:
                    break
            else:
                self.fail("helper did not finish after paste")
            self.assertEqual(os.waitstatus_to_exitcode(status), 0, output.decode())
            self.assertNotIn(b"SYNTHETIC_SIGNATURE", output)
            self.assertNotIn(data["access_token"].encode(), output)
            self.assertTrue(termios.tcgetattr(master)[3] & termios.ECHO)
            self.assertEqual(json.loads(self.path.read_text()), data)
        finally:
            if status is None or not ended:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            os.close(master)


if __name__ == "__main__":
    unittest.main()
