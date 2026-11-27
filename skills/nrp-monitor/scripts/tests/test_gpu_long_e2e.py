"""End to end for the NRP GPU rule (Hunter 2026-11-15): a fake `nrp-util-check` on PATH reports a low-GPU pod of a registered task, the
real check_pods pass runs, and the alarm must reach the owning chat as an order to stop the Job (not a DM to the owner), once an hour;
an undeliverable alarm DMs the owner at once; at 90 min (30 min after the warning) the monitor deletes the Job and fails the stage as util/gpu.
Run: python3 -m pytest tests/test_gpu_long_e2e.py"""
import argparse
import json
import os
import stat
from pathlib import Path
import types
from unittest.mock import patch

import pytest
from test_escalation_costs import monitor, task  # noqa: F401  (fixture)

POD = "work-17-abcde"
LINE = ("LOW %s age %dm, %dm mean: cpu 2.37/8.00 (30%%), mem 15.7/64.0Gi (25%%, max 55.7), gpu %d%% (gpu 1, NVIDIA A10) "
        "[NRP violation] rule=gpu")
FAKE = """#!/usr/bin/env python3
import os, sys
a = sys.argv
w = a[a.index("--window") + 1] if "--window" in a else "none"
p = os.path.join(os.environ["GPU_FAKE_DIR"], "window_%s.txt" % w)
out = open(p).read() if os.path.exists(p) else ""
with open(os.path.join(os.environ["GPU_FAKE_DIR"], "calls.txt"), "a") as f:
    f.write(" ".join(a[1:]) + "\\n")
sys.stdout.write(out)
sys.exit(4 if out.strip() else 0)
"""


@pytest.fixture
def env(monitor, tmp_path, monkeypatch):  # noqa: F811
    m = monitor
    fake = tmp_path / "bin"
    fake.mkdir()
    exe = fake / "nrp-util-check"
    exe.write_text(FAKE)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", "%s:%s" % (fake, os.environ["PATH"]))
    monkeypatch.setenv("GPU_FAKE_DIR", str(tmp_path))
    monkeypatch.delenv("NRP_MONITOR_NO_WAKE", raising=False)
    t = task(m)
    def live(v):
        v.update(failure=None, origin={"link": "t3-thread://v2/env1/coord-thread-1"})
        v["stages"][0].update(state="running")
    m.task_txn(t["name"], live)
    pushes, wakes, kube = [], [], []
    def kubectl(*args, **kwargs):
        kube.append(args)
        metadata = {"uid": "work-17-uid", "annotations": {"nrp.ai/username": "alice"}}
        return types.SimpleNamespace(returncode=0, stdout=json.dumps({"metadata": metadata}), stderr="")

    patches = [patch.object(m, "NS", t["namespace"]), patch.object(m, "USER_ANN", "alice"), patch.object(m, "push", side_effect=lambda msg, key, *a, **k: pushes.append((key, msg))),
               patch.object(m, "my_pods", return_value={POD: "work-17"}),
               patch.object(m, "kubectl", side_effect=kubectl),
               patch.object(m, "save_task_logs", return_value=None),
               patch.dict(m.WAKE_EXEC, {"t3-cli": lambda target, text: wakes.append((target, text))})]
    for p in patches:
        p.start()
    yield types.SimpleNamespace(m=m, dir=tmp_path, name=t["name"], pushes=pushes, wakes=wakes, kube=kube)
    for p in patches:
        p.stop()


def util(e, w60=None, w90=None):
    for w, line in ((60, w60), (90, w90)):
        p = e.dir / ("window_%d.txt" % w)
        p.write_text(line + "\n" if line else "")


def run_pass(e):
    a = argparse.Namespace(dry_run=False, fake_util=None)
    st = e.st if hasattr(e, "st") else {"jobs": {}, "pods": {}, "strikes": {}, "errors": 0}
    e.st = st
    e.m.check_pods(a, st)
    e.m.process_task_webhooks(a, st)


def test_1h_low_gpu_wakes_owning_chat_with_stop_order(env):
    util(env, w60=LINE % (POD, 70, 60, 30), w90=LINE % (POD, 70, 70, 30))
    run_pass(env)
    calls = (env.dir / "calls.txt").read_text()
    assert "--window 60" in calls and "--window 90" in calls and "--frac 0.4" in calls
    assert len(env.wakes) == 1, env.wakes
    target, text = env.wakes[0]
    assert target == {"harness": "t3-cli", "session": "coord-thread-1"}
    for must in ("GPU ALARM", "STOP THIS JOB NOW", "not a judgment call", POD, "30%", "three strikes", "90-min", "30 minutes"):
        assert must in text, must
    assert not env.pushes, env.pushes                                  # the agent acts; the owner is not paged
    t = env.m.task_load(env.name)
    assert not t.get("webhook_outbox")
    assert any("wake delivered: gpu_warning" in ev for ev in t["events"])
    assert not env.kube                                                # warn never deletes
    run_pass(env)                                                      # next pass, same hour: no repeat
    assert len(env.wakes) == 1


def test_undeliverable_alarm_dms_owner_on_first_failure(env):
    def down(target, text):
        raise env.m.WakeError("t3 unavailable (rc 1)")
    util(env, w60=LINE % (POD, 70, 60, 25))
    with patch.dict(env.m.WAKE_EXEC, {"t3-cli": down}):
        run_pass(env)
    keys = [k for k, _ in env.pushes]
    assert any(k.startswith("gpu-warn-undelivered:") for k in keys), env.pushes
    msg = dict(env.pushes)[keys[0]]
    assert "NOT DELIVERED" in msg and POD in msg
    assert env.m.task_load(env.name)["webhook_outbox"]                 # still retried to the chat
    run_pass(env)                                                      # retry delivers
    assert len(env.wakes) == 1 and "STOP THIS JOB NOW" in env.wakes[0][1]


def test_90min_low_gpu_deletes_job_and_fails_stage(env):
    util(env, w60=LINE % (POD, 100, 60, 30), w90=LINE % (POD, 100, 90, 35))
    run_pass(env)
    assert any(call[2:4] == ("delete", "--raw") and call[4].endswith("/jobs/work-17") for call in env.kube), env.kube
    t = env.m.task_load(env.name)
    assert t["stages"][0]["state"] == "failed"
    assert t["failure"]["cls"] == "util" and t["failure"].get("rule") == "gpu"
    assert "rule gpu" in t["stages"][0].get("util_deleted", "")
    assert any(k == "gpu-enforce:" + POD for k, _ in env.pushes)


def test_healthy_gpu_no_action(env):
    util(env)
    run_pass(env)
    assert not env.wakes and not env.pushes and not env.kube

def short_flag(e, age, reading=None):
    line = LINE % (POD, age, 10, 3)
    if reading is not None:
        line = line.replace("gpu 3% (gpu 1, NVIDIA A10)", reading)
    (e.dir / "window_none.txt").write_text(line + "\n")


@pytest.mark.parametrize("mode", ["auto", "watch"])
def test_short_gpu_safety_stop_without_agents(env, mode):
    m = env.m
    m.task_txn(env.name, lambda t: t.update(mode=mode))
    short_flag(env, 10)
    with patch.object(m, "run_task_agent", side_effect=AssertionError("GPU stop bypasses agents")), \
         patch.object(m, "save_task_logs", return_value=("saved.log", "")) as save:
        run_pass(env)
        m.advance_task(env.name, {}, argparse.Namespace(dry_run=False))
        run_pass(env)
        save.assert_called_once()
    assert sum(call[2:4] == ("delete", "--raw") for call in env.kube) == 1
    t = m.task_load(env.name)
    assert t["status"] == "WITH_COORDINATOR"
    assert t["stages"][0]["state"] == "failed"
    f = t["failure"]
    assert (f["cls"], f["sig"], f["rule"], f["logs"]) == ("util", "util:gpu", "gpu", "saved.log")
    assert len(env.wakes) == 1
    for fragment in ("10m", "GPU 3%", "NVIDIA A10", "CPU 30%", "CPU staging stage", "batching", "drop the GPU"):
        assert fragment in f["detail"]
        assert fragment in env.wakes[0][1]


def test_gpu_ramp_up_logs_once_then_enforces_without_pod_dedupe(env, monkeypatch):
    monkeypatch.setenv("NRP_MONITOR_GPU_RAMP_UP_MINUTES", "30")
    short_flag(env, 19)
    run_pass(env)
    run_pass(env)
    t = env.m.task_load(env.name)
    assert sum("GPU ramp-up wait" in entry for entry in t["events"]) == 1
    assert t["stages"][0]["state"] == "running"
    assert not t.get("util_event")
    assert not t.get("failure")
    assert not env.kube and not env.wakes
    short_flag(env, 20)
    run_pass(env)
    assert len(env.wakes) == 1
    assert env.m.task_load(env.name)["stages"][0]["state"] == "failed"


@pytest.mark.parametrize("reading", ["gpu ?(no DCGM series; unavailable)",
                                      "gpu 3% nvidia-smi max of 3 (no DCGM series; A10): re-check before deleting"])
def test_short_gpu_missing_dcgm_stays_in_review(env, monkeypatch, reading):
    short_flag(env, 20, reading)
    run_pass(env)
    m = env.m
    t = m.task_load(env.name)
    assert t["util_event"]["rule"] == "gpu"
    assert t["stages"][0]["state"] == "running"
    assert not t.get("failure")
    assert not env.kube and not env.wakes
    monkeypatch.setenv("NRP_TASK", env.name)
    with patch.object(m, "job_state", return_value="running"), \
         pytest.raises(SystemExit, match="without a measured DCGM flag"):
        m.cmd_tool(argparse.Namespace(rest=["delete", "work-17"]))
    assert not env.kube


def test_gpu_safety_stop_requires_changed_manifest_to_resubmit(env, monkeypatch, capsys):
    m = env.m
    short_flag(env, 11)
    run_pass(env)
    monkeypatch.setenv("NRP_TASK", env.name)
    args = argparse.Namespace(rest=["submit", "work-17", "--reason", "GPU staging bottleneck"])
    with patch.object(m, "manifest_check", return_value=[]), patch.object(m, "gpu_expired", return_value=None), \
         patch.object(m, "red_alert", return_value=False), patch.object(m, "job_state", return_value="missing"), \
         patch.object(m, "bad_nodes", return_value=[]), patch.object(m, "apply_manifest", return_value="ok") as apply:
        path = Path(m.task_load(env.name)["stages"][0]["manifest"])
        doc = json.loads(path.read_text())
        path.write_text(json.dumps(doc, indent=4, sort_keys=True))
        assert m.cmd_tool(args) == 1
        assert "GPU stage failed under NRP's 40% floor; resubmit needs a redesign" in capsys.readouterr().out
        apply.assert_not_called()
        doc["spec"]["template"]["spec"]["containers"][0]["args"].extend(["--prefetch-workers", "4"])
        path.write_text(json.dumps(doc))
        assert m.cmd_tool(args) == 0
        apply.assert_called_once()
    assert m.task_load(env.name)["stages"][0]["state"] == "running"


def test_gpu_stop_retries_failed_delete_without_repeating_wake(env):
    m = env.m
    short_flag(env, 11)
    with patch.object(m, "delete_owned_job", return_value=types.SimpleNamespace(returncode=1, stderr="Forbidden")):
        run_pass(env)
        run_pass(env)
    assert m.task_load(env.name)["stages"][0]["state"] == "running"
    assert len(env.wakes) == 1
    assert "DELETE FAILED" in env.wakes[0][1]

    run_pass(env)
    assert m.task_load(env.name)["failure"]["rule"] == "gpu"
    assert len(env.wakes) == 1


def test_short_gpu_flag_does_not_stop_same_named_job_in_another_namespace(env):
    m = env.m
    m.task_txn(env.name, lambda t: t.update(namespace="other"))
    short_flag(env, 11)
    run_pass(env)
    assert m.task_load(env.name)["stages"][0]["state"] == "running"
    assert not env.kube and not env.wakes


def test_gpu_reading_at_or_above_nrp_floor_is_not_a_safety_stop(monitor):  # noqa: F811
    """Only NRP's own 40% floor authorizes a stop; a stricter local lab floor goes to review instead."""
    util = monitor._modules["util"]
    line = LINE % (POD, 30, 10, 45)
    assert util.gpu_flag_action("no-such-task", "work", POD, line) is False


def test_unreadable_stop_fingerprint_does_not_block_resubmit_forever(monitor):  # noqa: F811
    sj = monitor._modules["stage_jobs"]
    doc = {"kind": "Job", "spec": {"x": 1}}
    assert sj.gpu_retry_unchanged({"gpu_stopped_fingerprint": sj.job_fingerprint(doc)}, doc) is True
    assert sj.gpu_retry_unchanged({"gpu_stopped_fingerprint": sj.job_fingerprint(doc)}, {"kind": "Job", "spec": {"x": 2}}) is False
    assert sj.gpu_retry_unchanged({"gpu_stopped_fingerprint": None}, doc) is False
    assert sj.gpu_retry_unchanged({}, doc) is False
