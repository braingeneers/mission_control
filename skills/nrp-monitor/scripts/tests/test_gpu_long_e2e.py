"""End to end for the NRP GPU rule (Hunter 2026-11-15): a fake `nrp-util-check` on PATH reports a low-GPU pod of a registered task, the
real check_pods pass runs, and the alarm must reach the owning chat as an order to stop the Job (not a DM to the owner), once an hour;
an undeliverable alarm DMs the owner at once; at 2.5 h the monitor deletes the Job and fails the stage as util/gpu.
Run: python3 -m pytest tests/test_gpu_long_e2e.py"""
import argparse
import os
import stat
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
    patches = [patch.object(m, "push", side_effect=lambda msg, key, *a, **k: pushes.append((key, msg))),
               patch.object(m, "my_pods", return_value={POD: "work-17"}),
               patch.object(m, "kubectl", side_effect=lambda *a, **k: kube.append(a) or types.SimpleNamespace(returncode=0, stdout="", stderr="")),
               patch.object(m, "save_task_logs", return_value=None),
               patch.dict(m.WAKE_EXEC, {"t3-cli": lambda target, text: wakes.append((target, text))})]
    for p in patches:
        p.start()
    yield types.SimpleNamespace(m=m, dir=tmp_path, name=t["name"], pushes=pushes, wakes=wakes, kube=kube)
    for p in patches:
        p.stop()


def util(e, w60=None, w150=None):
    for w, line in ((60, w60), (150, w150)):
        p = e.dir / ("window_%d.txt" % w)
        p.write_text(line + "\n" if line else "")


def run_pass(e):
    a = argparse.Namespace(dry_run=False, fake_util=None)
    st = e.st if hasattr(e, "st") else {"jobs": {}}
    e.st = st
    try:
        e.m.check_pods(a, st)
    except Exception as ex:  # the rest of check_pods (10-min strikes) is not under test; the GPU pass runs first
        e.check_pods_error = ex
    e.m.process_task_webhooks(a, st)


def test_1h_low_gpu_wakes_owning_chat_with_stop_order(env):
    util(env, w60=LINE % (POD, 70, 60, 30), w150=LINE % (POD, 70, 70, 30))
    run_pass(env)
    calls = (env.dir / "calls.txt").read_text()
    assert "--window 60" in calls and "--window 150" in calls and "--frac 0.4" in calls
    assert len(env.wakes) == 1, env.wakes
    target, text = env.wakes[0]
    assert target == {"harness": "t3-cli", "session": "coord-thread-1"}
    for must in ("GPU ALARM", "STOP THIS JOB NOW", "not a judgment call", POD, "30%", "three strikes", "150-min"):
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


def test_2p5h_low_gpu_deletes_job_and_fails_stage(env):
    util(env, w60=LINE % (POD, 160, 60, 30), w150=LINE % (POD, 160, 150, 35))
    run_pass(env)
    assert ("-n", env.m.NS, "delete", "job", "work-17", "--wait=false") in env.kube, env.kube
    t = env.m.task_load(env.name)
    assert t["stages"][0]["state"] == "failed"
    assert t["failure"]["cls"] == "util" and t["failure"].get("rule") == "gpu"
    assert "rule gpu" in t["stages"][0].get("util_deleted", "")
    assert any(k == "gpu-enforce:" + POD for k, _ in env.pushes)


def test_healthy_gpu_no_action(env):
    util(env)
    run_pass(env)
    assert not env.wakes and not env.pushes and not env.kube
