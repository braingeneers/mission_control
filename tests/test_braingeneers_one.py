"""Filesystem and upstream-contract tests; no network or personal skill changes."""

import base64
import importlib.util
import io
import json
from pathlib import Path
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
        patch.object(suite, "api", side_effect=self.api).start()
        patch.object(suite, "command", side_effect=self.command).start()
        self.manager = suite.Suite(self.root, self.base / "state", self.catalog)

    def source(self, name, version):
        key = (name, version)
        if key not in self.sources:
            files = {"SKILL.md": f"---\nname: {name}\ndescription: Example\n---\n\nInstructions {version}.\n".encode(),
                     "references/help.txt": f"Help {version}".encode()}
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
        self.assertFalse(result["complete"])

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
        for relative in ("SKILL.md", "references/help.txt", "new.txt"):
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

    def test_state_cannot_be_reused_for_another_root(self):
        self.manager.save()
        with self.assertRaisesRegex(suite.Failure, "different skills directory"):
            suite.Suite(self.base / "elsewhere", self.base / "state", self.catalog)

    def cli(self, *args):
        with patch.object(suite, "Suite", return_value=self.manager), patch.object(
                suite.sys, "argv", [str(SCRIPT), "--skills-dir", str(self.root),
                                    "--state-dir", str(self.base / "state"), *args]), patch(
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


if __name__ == "__main__":
    unittest.main()
