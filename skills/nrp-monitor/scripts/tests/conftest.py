"""Isolate wakes before collection and for every test, including child processes."""
import os
import tempfile
from pathlib import Path

import pytest
from test_isolation import wake_env

# Collection imports monitor modules too. Do not wait for a fixture to isolate HOME.
_COLLECTION_HOME = tempfile.TemporaryDirectory(prefix='nrp-tests-home-')
os.environ.update(wake_env(_COLLECTION_HOME.name))


@pytest.fixture(autouse=True)
def isolated_wakes(monkeypatch, tmp_path):
    env = wake_env(tmp_path / 'wake-isolation')
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv('PATH', str(Path(env['NRP_MONITOR_T3_BIN']).parent) + os.pathsep + os.environ['PATH'])
