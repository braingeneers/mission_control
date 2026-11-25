"""Isolate wakes before collection and for every test, including child processes."""
import os
import tempfile
from pathlib import Path

import pytest
from test_isolation import wake_env

# Collection imports monitor modules too. Do not wait for a fixture to isolate HOME.
_COLLECTION_HOME = tempfile.TemporaryDirectory(prefix='nrp-tests-home-')
os.environ.update(wake_env(_COLLECTION_HOME.name))
# A test that forgets to mock cluster or storage commands must fail locally.
_DENY_DIR = Path(_COLLECTION_HOME.name) / "deny-services"
_DENY_DIR.mkdir()
for name in ("kubectl", "aws"):
    executable = _DENY_DIR / name
    executable.write_text("#!/bin/sh\necho 'unexpected live service command in monitor test' >&2\nexit 1\n")
    executable.chmod(0o755)
os.environ["PATH"] = str(_DENY_DIR) + os.pathsep + os.environ["PATH"]
os.environ["KUBECONFIG"] = str(_DENY_DIR / "empty-kubeconfig")
(_DENY_DIR / "empty-kubeconfig").write_text("apiVersion: v1\nkind: Config\n")


@pytest.fixture(autouse=True)
def isolated_wakes(monkeypatch, tmp_path):
    env = wake_env(tmp_path / 'wake-isolation')
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('PATH', str(Path(env['NRP_MONITOR_T3_BIN']).parent) + os.pathsep + os.environ['PATH'])
