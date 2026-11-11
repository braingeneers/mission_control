"""Wake isolation shared by pytest and standalone unittest harnesses."""
import json
import os
from pathlib import Path

REAL_HOME = Path.home().resolve()


def wake_env(root, home=None):
    """Explicit recorders and a temporary HOME; never discover an installed wake CLI."""
    home = Path(home or root)
    root = Path(root).resolve()
    home.mkdir(parents=True, exist_ok=True)
    binaries = root / 'wake-bin'
    binaries.mkdir(parents=True, exist_ok=True)
    log = root / 'wake-calls.jsonl'
    for name in ('t3', 'claude', 'codex'):
        binary = binaries / name
        binary.write_text('#!/usr/bin/env python3\nimport json, sys\nfrom pathlib import Path\n'
                          + 'log = Path(%r)\n' % str(log)
                          + 'with log.open("a") as f:\n    f.write(json.dumps({"binary": %r, "argv": sys.argv[1:], "stdin": sys.stdin.read()}) + "\\n")\n' % name
                          + 'sys.exit(1)\n')
        binary.chmod(0o755)
    return {'HOME': str(home), 'NRP_MONITOR_TESTING': '1',
            'NRP_MONITOR_T3_BIN': str(binaries / 't3'),
            'NRP_MONITOR_CLAUDE_BIN': str(binaries / 'claude'),
            'NRP_MONITOR_CODEX_BIN': str(binaries / 'codex')}


def test_subprocess_harness_never_resolves_a_real_home_wake_binary():
    from unittest.mock import patch
    import test_tasks
    import test_agent_runners
    h = test_tasks.T()
    h.setUp()
    try:
        monitor = test_agent_runners.load_module(h.state)
        with patch.dict(os.environ, h.env, clear=True):
            for name in ('t3', 'claude', 'codex'):
                binary = Path(monitor.wake_binary(name)).resolve()
                assert binary.is_relative_to(h.tmp.resolve())
                assert not binary.is_relative_to(REAL_HOME)
            assert Path.home().resolve() == h.tmp.resolve()
    finally:
        h.tearDown()


def test_scratch_state_without_overrides_never_discovers_installed_clients(tmp_path):
    from unittest.mock import patch
    import pytest
    import test_agent_runners
    monitor = test_agent_runners.load_module(tmp_path / 'state')
    with patch.dict(os.environ, {'NRP_MONITOR_TESTING': '', 'NRP_MONITOR_T3_BIN': '',
                                'NRP_MONITOR_CLAUDE_BIN': '', 'NRP_MONITOR_CODEX_BIN': ''}), \
         patch.object(monitor.shutil, 'which', side_effect=AssertionError('PATH discovery forbidden')), \
         patch.object(monitor.Path, 'home', side_effect=AssertionError('HOME discovery forbidden')):
        for name in ('t3', 'claude', 'codex'):
            with pytest.raises(monitor.WakeError, match='explicit'):
                monitor.wake_binary(name)


def test_no_wake_disables_even_explicit_binaries(tmp_path):
    from unittest.mock import patch
    import pytest
    import test_agent_runners
    monitor = test_agent_runners.load_module(tmp_path / 'state')
    with patch.dict(os.environ, dict(wake_env(tmp_path), NRP_MONITOR_NO_WAKE='1')):
        with pytest.raises(monitor.WakeError, match='disabled'):
            monitor.wake_binary('t3')
