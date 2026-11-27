"""Monitor review regressions. Git uses temporary local repositories and services are mocked."""
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from nrp_monitor import cli, cluster, code_shipping as shipping, state
from nrp_monitor.task import registry


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, "")


@pytest.mark.parametrize("owner", [None, "bob", "alice"])
def test_delete_checks_annotation_and_uid(monkeypatch, owner):
    calls = []
    monkeypatch.setattr(state, "USER_ANN", "alice")

    def kubectl(*args, **kwargs):
        calls.append((args, kwargs))
        metadata = {"uid": "verified", "annotations": {"nrp.ai/username": owner}}
        return completed(json.dumps({"metadata": metadata})) if args[2] == "get" else completed()

    monkeypatch.setattr(cluster, "kubectl", kubectl)
    result = cluster.delete_owned_job("test", "alice-job")
    if owner == "alice":
        assert result.returncode == 0
        assert json.loads(calls[1][1]["input"])["preconditions"] == {"uid": "verified"}
    else:
        assert "does not match" in result.stderr
        assert len(calls) == 1


def test_kubectl_context_and_whoami(monkeypatch):
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return completed('{"status":{"userInfo":{"username":"alice"}}}')

    monkeypatch.setattr(state, "KUBE_CONTEXT", "alternate")
    monkeypatch.setattr(state, "USER_ANN", "")
    monkeypatch.setattr(state, "OWNER", {})
    monkeypatch.delenv("NRP_MONITOR_NRP_USERNAME", raising=False)
    monkeypatch.setattr(subprocess, "run", run)
    state.kube_username.cache_clear()
    try:
        assert state.nrp_username() == "alice"
        cluster.kubectl("get", "jobs")
        assert all(a[:3] == ["kubectl", "--context", "alternate"] for a in calls)
    finally:
        state.kube_username.cache_clear()


@pytest.mark.parametrize(("name", "job"), [("foreign", "alice-job"), ("alice-task", "foreign-job")])
def test_task_add_refuses_wrong_prefix(monkeypatch, name, job):
    monkeypatch.setenv("NRP_MONITOR_NRP_USERNAME", "alice")
    monkeypatch.setattr(registry, "validate_task", lambda *a, **k: {"name": name, "stages": [{"job": job}]})
    with pytest.raises(SystemExit, match="must start with alice-"):
        registry.task_add_raw({}, "TASK.json")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    clone = tmp_path / "clone"
    clone.mkdir()
    subprocess.run(["git", "init", "-qb", "work"], cwd=clone, check=True)
    (clone / "script.py").write_text("print(1)\n")
    subprocess.run(["git", "add", "script.py"], cwd=clone, check=True)
    shipping.checked_git(clone, "fixture commit failed", "commit", "-qm", "initial")
    monkeypatch.setenv("NRP_MONITOR_NRP_USERNAME", "alice")
    return clone, {"name": "alice-task", "code": {"clone": str(clone), "repo": str(clone), "branch": "work"}}


def test_staging_explicit_files_and_ref(repo, monkeypatch):
    clone, task = repo
    assert shipping.remote_ref(task) == "refs/heads/nrp-tasks/alice/alice-task"
    head = shipping.checked_git(clone, "head unavailable", "rev-parse", "HEAD")
    (clone / "script.py").write_text("print(2)\n")
    (clone / "stray.py").write_text("print('stray')\n")
    (clone / ".env.local").write_text("secret\n")
    with pytest.raises(state.ChainError, match="credential-like"):
        shipping.commit_code(task, "test", clone, [Path(".")], [".env.local"])
    with monkeypatch.context() as patch:
        patch.setattr(state, "CODE_SNAPSHOT_MAX", 1)
        with pytest.raises(state.ChainError, match="exceeds"):
            shipping.commit_code(task, "test", clone, [Path(".")])
        assert shipping.checked_git(clone, "head unavailable", "rev-parse", "HEAD") == head
    with monkeypatch.context() as patch:
        patch.setattr(state, "CODE_ARCHIVE_MAX", 32)
        with pytest.raises(state.ChainError, match="code archive exceeds"):
            shipping.commit_code(task, "test", clone, [Path(".")])
        assert shipping.checked_git(clone, "head unavailable", "rev-parse", "HEAD") == head
    shipped, _ = shipping.commit_code(task, "test", clone, [Path(".")])
    assert shipped != head
    assert not shipping.checked_git(clone, "tree unavailable", "ls-tree", shipped, "stray.py")
    declared, _ = shipping.commit_code(task, "test", clone, [Path(".")], ["stray.py"])
    assert shipping.checked_git(clone, "tree unavailable", "ls-tree", declared, "stray.py")


@pytest.mark.parametrize("age", [29, 31])
def test_bundle_age(monkeypatch, age):
    modified = datetime.now(timezone.utc) - timedelta(days=age)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: completed(json.dumps({"LastModified": modified.isoformat()})))
    assert shipping.bundle_fresh("s3://test/cache/a.tgz") == (age < 30)


def test_restore_keeps_tar_hash_with_different_gzip_level(repo, tmp_path, monkeypatch):
    clone, task = repo
    commit = shipping.checked_git(clone, "head unavailable", "rev-parse", "HEAD")
    archive = tmp_path / "old.tgz"
    _, tar_sha = shipping.pack(clone, commit, [Path(".")], archive)
    tar = gzip.decompress(archive.read_bytes())
    old_zip = gzip.compress(tar, compresslevel=1, mtime=0)
    old_sha = hashlib.sha256(old_zip).hexdigest()
    env = {shipping.URI_ENV: f"s3://test/cache/{old_sha}.tgz", shipping.SHA_ENV: old_sha,
           shipping.TAR_SHA_ENV: tar_sha, shipping.COMMIT_ENV: commit, shipping.DIRS_ENV: '["."]',
           shipping.PUSHED_ENV: "false", shipping.DIRTY_ENV: "true", shipping.REPO_ENV: "/laptop/task"}
    container = {"name": "worker"}
    shipping.rewrite_env(container, env)
    doc = {"kind": "Job", "metadata": {}, "spec": {"template": {"spec": {"containers": [container]}}}}
    monkeypatch.setattr(shipping, "bundle_fresh", lambda uri: False)
    monkeypatch.setattr(registry, "ensure_clone", lambda task: clone)
    monkeypatch.setattr(state, "task_txn", lambda *args: None)
    uploaded = []
    monkeypatch.setattr(shipping, "upload_code_archive", lambda path, uri: uploaded.append((path.read_bytes(), uri)))
    restored = shipping.ensure_bundle(task, {"id": "work"}, doc)
    data, uri = uploaded[0]
    assert gzip.decompress(data) == tar
    assert restored[shipping.SHA_ENV] == hashlib.sha256(data).hexdigest() != old_sha
    assert restored[shipping.TAR_SHA_ENV] == tar_sha
    assert restored[shipping.URI_ENV] == uri
    assert shipping.REPO_ENV not in restored
    assert not any(entry["name"] == shipping.REPO_ENV for entry in container["env"])


def test_failed_attempts_tagged_before_branch_removal(repo, tmp_path, monkeypatch):
    clone, task = repo
    remote = str(tmp_path / "upstream.git")
    subprocess.run(["git", "init", "--bare", "-q", remote], check=True)
    first = shipping.checked_git(clone, "head unavailable", "rev-parse", "HEAD")
    (clone / "script.py").write_text("print(2)\n")
    second, _ = shipping.commit_code(task, "work", clone, [Path(".")])
    ref = shipping.remote_ref(task)
    tag = shipping.provenance_tag(task, "work")
    shipping.checked_git(clone, "fixture push failed", "push", remote, first + ":" + tag, second + ":" + ref)
    attempts = [{shipping.COMMIT_ENV: sha, shipping.REMOTE_ENV: remote, shipping.PUSHED_ENV: "true"}
                for sha in (first, second)]
    task.update(status="failed", code_remote_heads={remote: {ref: second}},
                stages=[{"id": "work", "submitted_code_history": attempts}])
    monkeypatch.setattr(state, "task_txn", lambda *args: None)
    shipping.cleanup_task_code(task, dry_run=False)
    assert not (Path(remote) / ref).exists()
    assert (Path(remote) / tag).read_text().strip() == first
    assert (Path(remote) / (tag + "-" + second)).read_text().strip() == second


def test_status_reports_version_mismatch(tmp_path, monkeypatch, capsys):
    version = tmp_path / "VERSION"
    version.write_text("2.0\n")
    (tmp_path / "SKILL_VERSION_PATH").write_text(str(version))
    monkeypatch.setattr(state, "STATE", tmp_path)
    monkeypatch.setenv("NRP_MONITOR_BINARY_VERSION", "1.0")
    cli.warn_version_mismatch()
    assert "binary 1.0 differs from skill 2.0" in capsys.readouterr().out


def test_manifest_rejects_restart_ttl_storage_backoff_and_trailing_sleep(tmp_path):
    path = tmp_path / "job.json"
    path.write_text(json.dumps({
        "kind": "Job", "metadata": {"name": "alice-job"},
        "spec": {"activeDeadlineSeconds": 300, "backoffLimit": 1,
                 "template": {"spec": {"restartPolicy": "OnFailure", "containers": [
                     {"name": "worker", "command": ["sh", "-c", "run && sleep 1"],
                      "resources": {"requests": {"cpu": "1"}, "limits": {"cpu": "1"}}}]}}},
    }))
    problems = " ".join(registry.manifest_check(path, "test", "alice-job"))
    assert all(message in problems for message in
               ["backoffLimit", "ttlSecondsAfterFinished", "restartPolicy", "ephemeral-storage", "trailing"])


def test_preflight_runs_for_each_manifest_and_warns_once_when_missing(tmp_path, monkeypatch):
    script = tmp_path / "nrp_preflight.py"
    args = []
    monkeypatch.setenv("NRP_PREFLIGHT_PATH", str(script))
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: args.append(argv) or completed())
    task = {"stages": [{"manifest": name} for name in ("a.yaml", "b.yaml", "a.yaml")]}
    warnings = []
    registry.run_preflight(task, warnings)
    assert len(warnings) == 1 and not args
    script.touch()
    registry.run_preflight(task, [])
    assert [argv[-1] for argv in args] == ["a.yaml", "b.yaml"]
