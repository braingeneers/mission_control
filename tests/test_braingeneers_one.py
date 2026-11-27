"""Filesystem and upstream-contract tests; no network or personal skill changes."""

import base64
import importlib.util
import io
import json
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/braingeneers-one/scripts/suite.py"
spec = importlib.util.spec_from_file_location("braingeneers_suite", SCRIPT)
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


class MaintenanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "skills"
        self.root.mkdir()
        self.catalog = {name: {"name": name, "repo": "braingeneers/test",
                             "path": "skills/" + name, "branch": "main"}
                        for name in ("braingeneers-one", "example", "missing")}
        self.sources = {}
        self.latest_version = 1
        self.downloads = []
        self.api_calls = []
        self.fail_api = False
        self.fail_download = False
        self.during_download = lambda: None
        self.addCleanup(patch.stopall)
        patch.dict(suite.os.environ, {"HOME": str(self.base)}).start()
        patch.object(suite, "scheduler_command", return_value=False).start()
        patch.object(suite, "api", side_effect=self.api).start()
        patch.object(suite, "command", side_effect=self.command).start()
        self.manager = suite.Suite(self.root, self.base / "state", self.catalog)

    def source(self, name, version):
        key = (name, version)
        if key not in self.sources:
            files = {"SKILL.md": f"---\nname: {name}\ndescription: Example\n---\n\nInstructions {version}.\n".encode(),
                     "references/help.txt": f"Help {version}".encode(),
                     "scripts/_vendor/yaml/loader.py": b"# Bundled reader fixture\n"}
            tree = suite.hashlib.sha1((name + str(version)).encode()).hexdigest()
            self.sources[key] = (tree, files)
        return self.sources[key]

    def write_install(self, root, name, version, pinned=None):
        tree, files = self.source(name, version)
        folder = root / name
        for relative, content in files.items():
            if relative == "SKILL.md":
                header, body = suite.frontmatter(content)
                header["metadata"] = {"github-repo": "https://github.com/braingeneers/test",
                                      "github-path": "skills/" + name,
                                      "github-ref": "refs/heads/main", "github-tree-sha": tree}
                if pinned:
                    header["metadata"]["github-pinned"] = pinned
                content = ("---\n" + suite.yaml.safe_dump(header) + "---\n\n" + body).encode()
            file = folder / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
        return folder

    def api(self, endpoint):
        self.api_calls.append(endpoint)
        if self.fail_api:
            raise suite.Failure("Network unavailable")
        if "/commits/main" in endpoint:
            return {"sha": str(self.latest_version) * 40}
        if "/contents/skills?ref=" in endpoint:
            version = int(endpoint[-1])
            return [{"name": name, "type": "dir", "sha": self.source(name, version)[0]}
                    for name in self.catalog]
        for tree, files in self.sources.values():
            if "/git/trees/" + tree in endpoint:
                return {"truncated": False, "tree": [
                    {"path": path, "type": "blob", "mode": "100644", "sha": suite.blob_sha(data)}
                    for path, data in files.items()]}
            for data in files.values():
                if endpoint.endswith("/git/blobs/" + suite.blob_sha(data)):
                    return {"content": base64.b64encode(data).decode()}
        raise AssertionError(endpoint)

    def command(self, args, cwd=None):
        self.assertEqual(args[:3], ["gh", "skill", "install"])
        self.assertNotIn("--force", args)
        if self.fail_download:
            raise suite.Failure("Download failed")
        path, commit = args[4].split("@")
        name = Path(path).name
        self.downloads.append(name)
        self.write_install(Path(args[6]), name, int(commit[0]))
        self.during_download()
        return ""

    def test_first_install_and_current_status(self):
        result = self.manager.install("example")
        self.assertEqual(result["status"], "installed")
        self.assertTrue((self.root / "example/SKILL.md").exists())
        rows = self.manager.status()["results"]
        self.assertEqual(rows[1]["status"], "current")
        self.assertEqual(rows[2]["status"], "not installed")

    def test_unknown_but_pristine_install_is_verified_then_updatable(self):
        self.write_install(self.root, "example", 1)
        self.assertTrue(self.manager.status()["complete"])
        self.latest_version = 2
        self.assertEqual(self.manager.status()["results"][1]["status"], "update available")
        previous = suite.fingerprint(self.root / "example")
        result = self.manager.install("example", update=True)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(suite.fingerprint(Path(result["backup"])), previous)
        self.assertNotEqual(suite.fingerprint(self.root / "example"), previous)
        self.assertFalse((self.root / "missing").exists())

    def test_daily_check_caches_success_but_detects_local_edits(self):
        self.write_install(self.root, "example", 1)
        self.manager.status(daily=True)
        count = len(self.api_calls)
        self.assertTrue(self.manager.status(daily=True)["cached"])
        self.assertEqual(len(self.api_calls), count)
        (self.root / "example/references/help.txt").write_text("local edit")
        result = self.manager.status(daily=True)
        self.assertFalse(result["cached"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["results"][1]["state"], "stuck")

    def test_network_failure_does_not_claim_success_and_explicit_check_retries(self):
        self.write_install(self.root, "example", 1)
        self.fail_api = True
        self.assertFalse(self.manager.status(daily=True)["complete"])
        self.fail_api = False
        self.assertFalse(self.manager.status(daily=True)["complete"])
        self.assertTrue(self.manager.status()["complete"])

    def test_daily_cache_expires_and_finds_new_upstream_version(self):
        self.write_install(self.root, "example", 1)
        first = self.manager.status(daily=True)
        self.latest_version = 2
        with patch.object(suite.time, "time", return_value=first["time"] + 86401):
            result = self.manager.status(daily=True)
        self.assertFalse(result["cached"])
        self.assertEqual(result["results"][1]["status"], "update available")

    def test_failed_download_preserves_installed_version_and_fingerprint(self):
        self.manager.install("example")
        before = suite.fingerprint(self.root / "example")
        self.latest_version = 2
        self.fail_download = True
        with self.assertRaises(suite.Failure):
            self.manager.install("example", update=True)
        self.assertEqual(suite.fingerprint(self.root / "example"), before)
        self.assertEqual(self.manager.state["managed"]["example"]["files"], before)

    def test_missing_skill_failed_download_leaves_no_installation(self):
        self.fail_download = True
        with self.assertRaises(suite.Failure):
            self.manager.install("example")
        self.assertFalse((self.root / "example").exists())

    def test_corrupted_staged_files_never_replace_installed_skill(self):
        self.write_install(self.root, "example", 1)
        before = suite.fingerprint(self.root / "example")
        self.latest_version = 2

        def corrupt_download():
            for file in self.root.glob(".braingeneers-stage-*/example/references/help.txt"):
                file.write_text("corrupted download")

        self.during_download = corrupt_download
        with self.assertRaisesRegex(suite.Failure, "modified"):
            self.manager.install("example", update=True)
        self.assertEqual(suite.fingerprint(self.root / "example"), before)

    def test_local_edits_and_extra_files_prevent_enrollment(self):
        for relative in ("SKILL.md", "references/help.txt", "new.txt", "scripts/_vendor/yaml/loader.py"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory(dir=self.base) as other:
                manager = suite.Suite(Path(other), self.base / (relative.replace("/", "-") + "-state"), self.catalog)
                folder = self.write_install(Path(other), "example", 1)
                (folder / relative).write_text("local work")
                before = suite.fingerprint(folder)
                with self.assertRaises(suite.Failure):
                    manager.install("example", update=True)
                self.assertEqual(suite.fingerprint(folder), before)
                self.assertNotIn("example", manager.state["managed"])

    def test_managed_edits_are_preserved(self):
        self.manager.install("example")
        (self.root / "example/references/help.txt").write_text("changed")
        self.latest_version = 2
        with self.assertRaises(suite.Failure):
            self.manager.install("example", update=True)
        self.assertEqual((self.root / "example/references/help.txt").read_text(), "changed")

    def test_pins_symlinks_and_wrong_source_are_preserved(self):
        folder = self.write_install(self.root, "example", 1, pinned="v1")
        with self.assertRaisesRegex(suite.Failure, "pinned"):
            self.manager.install("example", update=True)
        target = self.base / "owner-checkout"
        folder.rename(target)
        folder.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(suite.Failure, "Symlink"):
            self.manager.install("example", update=True)
        self.assertTrue(folder.is_symlink())
        other = self.write_install(self.root, "missing", 1)
        file = other / "SKILL.md"
        file.write_text(file.read_text().replace("braingeneers/test", "other/source"))
        with self.assertRaisesRegex(suite.Failure, "Unknown source"):
            self.manager.install("missing", update=True)

    def test_changes_during_download_are_preserved(self):
        self.manager.install("example")
        self.latest_version = 2
        self.during_download = lambda: (self.root / "example/new.txt").write_text("concurrent work")
        with self.assertRaisesRegex(suite.Failure, "changed while"):
            self.manager.install("example", update=True)
        self.assertEqual((self.root / "example/new.txt").read_text(), "concurrent work")

    def test_unrelated_skills_untouched_and_absent_update_is_noop(self):
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        (unrelated / "SKILL.md").write_text("personal skill")
        self.manager.status()
        self.assertEqual(self.manager.install("missing", update=True)["status"], "not installed; left absent")
        self.assertEqual((unrelated / "SKILL.md").read_text(), "personal skill")
        self.assertEqual(self.downloads, [])

    def test_malformed_skill_does_not_hide_other_results(self):
        (self.root / "example").mkdir()
        self.write_install(self.root, "missing", 1)
        rows = self.manager.status()["results"]
        self.assertEqual(rows[1]["status"], "skipped / freshness unknown")
        self.assertEqual(rows[2]["status"], "current")

    def test_invalid_or_unsafe_yaml_does_not_claim_current_or_hide_other_results(self):
        self.write_install(self.root, "missing", 1)
        folder = self.write_install(self.root, "example", 1)
        for header in ("name: [unclosed", "name: !!python/tuple [1, 2]"):
            with self.subTest(header=header):
                (folder / "SKILL.md").write_text("---\n" + header + "\n---\nInstructions\n")
                result = self.manager.status()
                self.assertFalse(result["complete"])
                self.assertEqual(result["results"][1]["status"], "skipped / freshness unknown")
                self.assertEqual(result["results"][2]["status"], "current")

    def test_state_cannot_be_reused_for_another_root(self):
        self.manager.save()
        with self.assertRaisesRegex(suite.Failure, "different skills directory"):
            suite.Suite(self.base / "elsewhere", self.base / "state", self.catalog)

    def cli(self, *args):
        with patch.object(suite, "Suite", return_value=self.manager), patch.object(
                suite.sys, "argv", [str(SCRIPT), "--skills-dir", str(self.root),
                                    "--state-dir", str(self.manager.state_dir), *args]), patch(
                "sys.stdout", new_callable=io.StringIO) as output:
            code = suite.main()
            return code, output.getvalue()

    def test_cli_updates_router_last_and_leaves_missing_members_absent(self):
        for name in ("braingeneers-one", "example"):
            self.write_install(self.root, name, 1)
        self.latest_version = 2
        code, output = self.cli("update")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.downloads, ["example", "braingeneers-one"])
        self.assertFalse((self.root / "missing").exists())
        self.assertFalse((self.base / "state/running.lock").exists())

    def test_auto_only_updates_behind_managed_copies(self):
        self.manager.install("example")
        self.manager.install("braingeneers-one")
        edited = self.root / "braingeneers-one/references/help.txt"
        edited.write_text("local work")
        unmanaged = self.write_install(self.root, "missing", 1)
        self.latest_version = 2
        self.downloads.clear()
        self.assertEqual(self.cli("update", "--auto"), (0, "Updated Braingeneers skills: example\n"))
        self.assertEqual(self.downloads, ["example"])
        self.assertEqual(edited.read_text(), "local work")
        self.assertNotIn("missing", self.manager.state["managed"])
        self.assertEqual((unmanaged / "references/help.txt").read_text(), "Help 1")
        self.assertEqual(self.cli("update", "--auto"), (0, ""))

    def test_auto_skips_links_even_with_a_managed_record_and_reports_real_errors(self):
        for name in ("example", "braingeneers-one"):
            self.manager.install(name)
        link = self.root / "example"
        target = self.base / "owner-checkout"
        link.rename(target)
        link.symlink_to(target, target_is_directory=True)
        self.latest_version = 2
        self.downloads.clear()
        self.fail_api = True
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(self.cli("update", "--auto"), (1, ""))
        self.assertEqual(stderr.getvalue(), "braingeneers-one: Network unavailable\n")
        self.assertEqual(self.downloads, [])
        self.assertEqual(link.readlink(), target)
        self.assertEqual((target / "references/help.txt").read_text(), "Help 1")

    def test_auto_updates_shared_copy_through_existing_codex_link(self):
        root = self.base / ".claude/skills"
        manager = suite.Suite(root, self.base / "shared-state", self.catalog)
        installed = manager.install("example")
        link = Path(installed["codex_link"])
        self.assertEqual(link.readlink(), root / "example")
        original_link = link.lstat()
        self.latest_version = 2
        self.root, self.manager = root, manager
        self.assertEqual(self.cli("update", "--auto"), (0, "Updated Braingeneers skills: example\n"))
        self.assertTrue(suite.os.path.samestat(original_link, link.lstat()))
        self.assertEqual((link / "references/help.txt").read_text(), "Help 2")

    def test_reset_backs_up_modified_copy_and_reports_local_changes(self):
        self.manager.install("example")
        folder = self.root / "example"
        (folder / "references/help.txt").write_text("local edit")
        (folder / "my-link").symlink_to(self.base / "personal-file")
        (folder / "scripts/_vendor/yaml/loader.py").unlink()
        self.latest_version = 2
        code, output = self.cli("reset", "example")
        self.assertEqual(code, 0, output)
        row, = json.loads(output)
        backup = Path(row["backup"])
        self.assertEqual(backup.parent, self.manager.state_dir / "backups")
        self.assertEqual((backup / "references/help.txt").read_text(), "local edit")
        self.assertTrue((backup / "my-link").is_symlink())
        self.assertEqual((folder / "references/help.txt").read_text(), "Help 2")
        self.assertEqual(Path(row["diff_summary"]).read_text().splitlines(), [
            "added 'my-link'", "modified 'references/help.txt'", "removed 'scripts/_vendor/yaml/loader.py'"])
        self.assertEqual(self.manager.status()["results"][1]["state"], "current")

    def test_status_table_and_preservation_across_operations(self):
        self.manager.install("example")
        (self.root / "example/references/help.txt").write_text("local edit")
        local = self.root / "braingeneers-one"
        local.mkdir()
        (local / "SKILL.md").write_text("owner-managed")
        target = self.base / "missing-checkout"
        link = self.root / "missing"
        link.symlink_to(target, target_is_directory=True)
        good = self.root / "live-link"
        good.symlink_to(local, target_is_directory=True)
        (self.root / "synced").mkdir()
        before = suite.fingerprint(local)
        self.downloads.clear()
        for name in ("missing", "braingeneers-one"):
            self.assertEqual(self.cli("install", name)[0], 0)
            self.assertEqual(self.cli("update", name)[0], 1)
            self.assertEqual(self.cli("reset", name)[0], 1)
        self.assertEqual(self.cli("update", "--auto"), (0, ""))
        self.assertEqual(link.readlink(), target)
        self.assertEqual(suite.fingerprint(local), before)
        self.assertEqual(self.downloads, [])
        with patch.dict(suite.os.environ, {"HOME": str(self.base)}):
            codex = self.base / ".agents/skills"
            codex.mkdir(parents=True)
            (codex / "example").symlink_to(self.root / "example", target_is_directory=True)
            code, output = self.cli("status", "--table")
            self.assertEqual(code, 1, output)  # Local SKILL.md has no valid frontmatter.
            for label in ("modified copy", "external link", "dangling link", "unmanaged dir",
                          "DANGLING LINK", "reset example", "ok"):
                self.assertIn(label, output)
            self.assertNotIn("synced", output)
            _, output = self.cli("status", "--json")
            rows = {row["name"]: row for row in json.loads(output)["results"]}
            self.assertEqual(rows["example"]["codex_link"], "ok")
            self.assertEqual(rows["missing"]["state"], "stuck")
            self.assertEqual(rows["missing"]["source"], str(target))

    def test_macos_schedule_uses_temporary_home_and_mock_launchctl(self):
        runner = self.root / "braingeneers-one/scripts/suite.py"
        runner.parent.mkdir(parents=True)
        runner.touch()
        plist = self.base / "Library/LaunchAgents" / (suite.SCHEDULE_LABEL + ".plist")
        with patch.dict(suite.os.environ, {"HOME": str(self.base)}), patch.object(
                suite.sys, "platform", "darwin"), patch.object(suite, "scheduler_command") as scheduler:
            scheduler.side_effect = lambda args, **kwargs: len(args[-1].split("/")) == 2
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(self.cli("install", "braingeneers-one")[0], 0)
                self.assertEqual(stderr.getvalue(), "Daily updates enabled.\n")
            data = plistlib.loads(plist.read_bytes())
            self.assertEqual(data["ProgramArguments"], [
                sys.executable, str(runner), "--skills-dir", str(self.root),
                "--state-dir", str(self.base / "state"), "update", "--auto"])
            self.assertEqual(data["StartCalendarInterval"], {"Hour": 9, "Minute": 0})
            self.assertEqual(scheduler.call_args.args[0][:2], ["launchctl", "bootstrap"])
            scheduler.side_effect = None
            scheduler.return_value = True
            self.assertEqual(self.cli("schedule", "status"), (0, "Daily updates enabled.\n"))
            self.assertEqual(self.cli("schedule", "disable"), (0, "Daily updates disabled.\n"))
            self.assertEqual(scheduler.call_args.args[0][:2], ["launchctl", "bootout"])
            self.assertFalse(plist.exists())

    def test_linux_schedule_timer_and_cron_fallback(self):
        runner = self.root / "braingeneers-one/scripts/suite.py"
        runner.parent.mkdir(parents=True)
        runner.touch()
        config = self.base / "config dir"
        directory = config / "systemd/user"
        with patch.dict(suite.os.environ, {"HOME": str(self.base), "XDG_CONFIG_HOME": str(config)}), patch.object(
                suite.sys, "platform", "linux"), patch.object(suite, "scheduler_command") as scheduler:
            self.assertEqual(self.cli("schedule", "enable"), (0, "Daily updates enabled.\n"))
            service = directory / (suite.SCHEDULE_LABEL + ".service")
            timer = directory / (suite.SCHEDULE_LABEL + ".timer")
            self.assertIn(f'"{runner}"', service.read_text())
            self.assertIn('"update" "--auto"', service.read_text())
            self.assertIn("OnCalendar=*-*-* 09:00:00", timer.read_text())
            self.assertEqual(self.cli("schedule", "status"), (0, "Daily updates enabled.\n"))
            self.assertEqual(self.cli("schedule", "disable"), (0, "Daily updates disabled.\n"))
            self.assertFalse(service.exists())
            self.assertFalse(timer.exists())
            scheduler.return_value = False
            code, output = self.cli("schedule", "enable")
            self.assertEqual(code, 0, output)
            self.assertIn("0 9 * * * ", output)
            self.assertIn("update --auto", output)
            self.assertFalse(timer.exists())

    def test_install_and_update_ensure_schedule_until_user_disables_it(self):
        runner = self.write_install(self.root, "braingeneers-one", 1) / "scripts/suite.py"
        runner.touch()
        self.write_install(self.root, "example", 1)
        for operation in ("install", "update"):
            with self.subTest(operation=operation), patch.object(suite.sys, "platform", "linux"), patch.dict(
                    suite.os.environ, {"XDG_CONFIG_HOME": str(self.base / operation)}), patch.object(
                    suite, "scheduler_command") as scheduler, patch("sys.stderr", new_callable=io.StringIO):
                scheduler.side_effect = lambda args, **kwargs: not any(
                    status in args for status in ("is-enabled", "is-active"))
                self.assertEqual(self.cli(operation, "example")[0], 0)
                timer = self.base / operation / "systemd/user" / (suite.SCHEDULE_LABEL + ".timer")
                self.assertTrue(timer.is_file())
                self.assertIn("enable", scheduler.call_args.args[0])
                scheduler.side_effect = None
                scheduler.return_value = True
                scheduler.reset_mock()
                self.assertEqual(self.cli("update", "example")[0], 0)
                self.assertEqual(scheduler.call_count, 3)
                self.assertEqual(self.cli("schedule", "disable")[0], 0)
                self.assertFalse(timer.exists())
                scheduler.reset_mock()
                self.assertEqual(self.cli("update", "example")[0], 0)
                self.assertEqual(self.cli("install", "example")[0], 0)
                self.assertEqual(self.cli("update", "--auto"), (0, ""))
                scheduler.assert_not_called()
                self.assertEqual(self.cli("schedule", "enable")[0], 0)
                self.assertFalse((self.manager.state_dir / "auto-update-disabled").exists())

    def test_cli_rejects_non_catalog_member_before_download(self):
        with patch("sys.stderr", new_callable=io.StringIO):
            code, _ = self.cli("install", "untrusted")
        self.assertEqual(code, 1)
        self.assertEqual(self.downloads, [])

    def test_lock_prevents_concurrent_helper(self):
        (self.base / "state/running.lock").mkdir(parents=True)
        with self.assertRaisesRegex(SystemExit, "Another helper"):
            self.cli("install", "example")
        self.assertEqual(self.downloads, [])

    def test_replacement_failure_restores_previous_installation(self):
        self.write_install(self.root, "example", 1)
        before = suite.fingerprint(self.root / "example")
        self.latest_version = 2
        real_rename = Path.rename

        def fail_staged_move(path, target):
            if ".braingeneers-stage-" in str(path):
                raise OSError("Simulated rename failure")
            return real_rename(path, target)

        with patch.object(Path, "rename", fail_staged_move), self.assertRaises(OSError):
            self.manager.install("example", update=True)
        self.assertEqual(suite.fingerprint(self.root / "example"), before)


class PortabilityTest(unittest.TestCase):
    def test_bundled_reader_without_site_packages_or_pip(self):
        # -I -S disables user paths and all site-packages. An existing 'yaml'
        # module must not divert imports away from the bundled reader.
        program = '''
import importlib.util, json, runpy, sys, types
assert importlib.util.find_spec("pip") is None
assert importlib.util.find_spec("yaml") is None
sys.modules["yaml"] = types.ModuleType("yaml")
before = sys.dont_write_bytecode
helper = runpy.run_path(sys.argv[1], run_name="portability_test")
reader = helper["yaml"]
assert sys.dont_write_bytecode == before
assert reader.__version__ == "6.0.3"
assert not reader.__with_libyaml__
header, body = helper["frontmatter"](b"---\\nname: example\\ndescription: >\\n  Multiple lines\\n  of text\\nmetadata:\\n  nested: {flag: true}\\n---\\nBody\\n")
assert header["description"] == "Multiple lines of text\\n"
assert header["metadata"]["nested"]["flag"] is True
assert reader.safe_load(reader.safe_dump(header)) == header
print(json.dumps({"reader": reader.__file__, "body": body}))
'''
        with tempfile.TemporaryDirectory(prefix="braingeneers portability ") as temporary:
            copy = Path(temporary) / "skill with spaces"
            shutil.copytree(SCRIPT.parents[1], copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            before = suite.fingerprint(copy)
            result = subprocess.run([sys.executable, "-I", "-S", "-c", program,
                                     str(copy / "scripts/suite.py")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)["reader"]).relative_to(copy).as_posix(),
                             "scripts/_vendor/yaml/__init__.py")
            self.assertEqual(suite.fingerprint(copy), before)

    def test_cli_without_packages_or_github_cli_preserves_skill_contents(self):
        with tempfile.TemporaryDirectory(prefix="braingeneers cli ") as temporary:
            base = Path(temporary)
            root = base / "skills with spaces"
            copy = root / "braingeneers-one"
            shutil.copytree(SCRIPT.parents[1], copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            file = copy / "SKILL.md"
            header, body = suite.frontmatter(file.read_bytes())
            header["metadata"] = {"github-repo": "https://github.com/braingeneers/mission_control",
                                  "github-path": "skills/braingeneers-one", "github-tree-sha": "a" * 40}
            file.write_text("---\n" + suite.yaml.safe_dump(header) + "---\n" + body)
            before = suite.fingerprint(copy)
            empty_path = base / "empty path"
            empty_path.mkdir()
            result = subprocess.run([sys.executable, "-I", "-S", str(copy / "scripts/suite.py"),
                                     "--skills-dir", str(root),
                                     "--state-dir", str(base / "state with spaces"), "status"],
                                    env={**suite.os.environ, "PATH": str(empty_path)},
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            output = json.loads(result.stdout)
            self.assertFalse(output["complete"])
            self.assertEqual(output["results"][0]["status"], "skipped / freshness unknown")
            self.assertIn("GitHub CLI unavailable", output["results"][0]["reason"])
            self.assertEqual(suite.fingerprint(copy), before)
            self.assertFalse((base / "state with spaces/running.lock").exists())

    def test_github_failures_are_bounded_and_do_not_expose_command_output(self):
        for failure in (FileNotFoundError(), subprocess.TimeoutExpired("gh", 180)):
            with self.subTest(failure=failure), patch.object(suite.subprocess, "run", side_effect=failure):
                with self.assertRaisesRegex(suite.Failure, "unavailable or timed out"):
                    suite.command(["gh", "api", "example"])
        response = subprocess.CompletedProcess(["gh"], 1, "private output", "private error")
        with patch.object(suite.subprocess, "run", return_value=response):
            with self.assertRaises(suite.Failure) as caught:
                suite.command(["gh", "api", "example"])
        self.assertIn("repository access", str(caught.exception))
        self.assertNotIn("private", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
