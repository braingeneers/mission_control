"""Task clone pruning, restore from bundle, snapshot-aware fix count, and the whole-repo checkout limit."""
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nrp_monitor import state  # noqa: E402
from nrp_monitor.task import cleanup, registry  # noqa: E402

DAY = 86400


def sh(cwd, *args):
    r = subprocess.run(["git", *state.GIT_ID, *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE", tmp_path / "state")
    monkeypatch.setattr(state, "TASKS", tmp_path / "state" / "tasks")
    monkeypatch.setattr(state, "TASK_CACHE", tmp_path / "cache")
    monkeypatch.setattr(state, "LOG", tmp_path / "state" / "monitor.log", raising=False)
    monkeypatch.setattr(state, "SLOCK", tmp_path / "state" / "state.lock", raising=False)
    digests = []
    monkeypatch.setattr("nrp_monitor.notify.digest", lambda kind, msg, task="-": digests.append((kind, msg, task)))
    repo = tmp_path / "src"
    (repo / "job").mkdir(parents=True)
    (repo / "other").mkdir()
    (repo / "job" / "run.py").write_text("print(1)\n")
    (repo / "other" / "big.txt").write_text("x" * 5000)
    sh(tmp_path, "init", "-q", "-b", "main", str(repo))
    sh(repo, "add", "-A")
    sh(repo, "commit", "-qm", "init")
    return SimpleNamespace(tmp=tmp_path, repo=repo, digests=digests)


def add(env, name, code=None, status="done", ended_days=10, **extra):
    warn = []
    c = registry.clone_code(name, dict({"repo": str(env.repo), "subdir": "job"}, **(code or {})), warn)
    t = dict({"name": name, "status": status, "code": c, "terminal_at": state.now() - ended_days * DAY}, **extra)
    state.task_write(t)
    return t


def prune(now=None):
    (state.STATE / "clone-prune.stamp").unlink(missing_ok=True)
    cleanup.prune_clones(SimpleNamespace(dry_run=False), now=now)


def test_snapshot_excludes_task_add_commits(env):
    (env.repo / "job" / "run.py").write_text("print(2)\n")              # uncommitted: becomes a task-add commit
    t = add(env, "t1")
    c = t["code"]
    assert c["snapshot"] != c["base"]
    assert sh(c["clone"], "rev-list", "--count", "%s..HEAD" % c["snapshot"]) == "0"


def test_prune_age_limits_and_running_reference(env):
    add(env, "young", ended_days=1)
    add(env, "old", ended_days=4)
    add(env, "cont", ended_days=4, on_done={"plan": "p", "from_step": "1"})
    parent = add(env, "parent", ended_days=30)
    add(env, "child", code={"repo": parent["code"]["clone"]}, status="running")
    prune()
    assert Path(state.task_load("young")["code"]["clone"]).exists()
    assert not Path(state.task_load("old")["code"]["clone"]).exists()
    assert state.task_load("old")["code"]["pruned_at"]
    assert state.task_load("old")["code"]["bundle"] is None                # clean clone: nothing to keep
    assert Path(state.task_load("cont")["code"]["clone"]).exists()         # continuation may still come
    assert Path(parent["code"]["clone"]).exists()                          # a running task clones from it
    assert Path(state.task_load("child")["code"]["clone"]).exists()
    prune(now=state.now() + 4 * DAY)
    assert not Path(state.task_load("cont")["code"]["clone"]).exists()
    assert (state.STATE / "clone-cache.json").exists()


def test_fix_is_bundled_digested_and_restored(env):
    t = add(env, "fixed")
    clone = t["code"]["clone"]
    Path(clone, "job", "run.py").write_text("print('fixed')\n")
    sh(clone, "commit", "-qam", "monitor fix")
    head = sh(clone, "rev-parse", "HEAD")
    prune()
    t = state.task_load("fixed")
    assert not Path(clone).exists()
    assert Path(t["code"]["bundle"]).exists() and t["code"]["final"] == head
    assert any(k == "merge" and "bundle" in m for k, m, _ in env.digests)
    registry.ensure_clone(t)
    assert sh(clone, "rev-parse", "HEAD") == head
    assert sh(clone, "branch", "--show-current") == t["code"]["branch"]
    assert Path(clone, "job", "run.py").read_text() == "print('fixed')\n"
    assert not Path(clone, "other").exists()                               # same sparse scope as at task add


def test_restore_walks_a_pruned_parent_chain(env):
    parent = add(env, "p1", ended_days=30)
    child = add(env, "c1", code={"repo": parent["code"]["clone"]}, ended_days=30)
    prune()
    assert not Path(parent["code"]["clone"]).exists() and not Path(child["code"]["clone"]).exists()
    registry.ensure_clone(state.task_load("c1"))
    assert Path(child["code"]["clone"], "job", "run.py").exists()


def test_full_checkout_limit(env, monkeypatch):
    monkeypatch.setattr(state, "CLONE_FULL_MAX", 1000)
    with pytest.raises(state.ChainError, match="code.subdir"):
        registry.clone_code("whole", {"repo": str(env.repo)}, [])
    c = registry.clone_code("whole", {"repo": str(env.repo), "full_checkout": True}, [])
    assert Path(c["clone"], "other", "big.txt").exists() and c["full_checkout"]
    registry.clone_code("narrow", {"repo": str(env.repo), "subdir": "job"}, [])


def test_missing_clone_does_not_break_postcheck(env):
    from nrp_monitor.task import pass_
    t = add(env, "gone")
    t["postcheck"] = {"cmd": ["true"], "expect": ""}
    prune()
    assert pass_.run_postcheck(t)["ok"]


def test_registering_from_a_pruned_clone_restores_it(env):
    parent = add(env, "smoke", ended_days=30)                              # a plan TASK file names this clone as its repo
    prune()
    assert not Path(parent["code"]["clone"]).exists()
    c = registry.clone_code("full", {"repo": parent["code"]["clone"], "subdir": "job"}, [])
    assert Path(c["clone"], "job", "run.py").exists() and Path(parent["code"]["clone"]).exists()
