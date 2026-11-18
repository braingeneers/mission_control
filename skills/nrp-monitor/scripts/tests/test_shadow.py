"""Shadow IO boundaries: no real cluster/network/agents used."""
import importlib
import json
from pathlib import Path
import subprocess
import tempfile
import urllib.request

import pytest
from nrp_monitor import shadow, state


@pytest.fixture
def isolated(monkeypatch):
    base = Path('/private/tmp/claude-501/nrp-shadow')
    base.mkdir(parents=True, exist_ok=True)
    # Keep disposable fixtures for audit, as with live snapshots; never installed state.
    dest = Path(tempfile.mkdtemp(prefix='test-', dir=base))
    monkeypatch.setattr(state, 'STATE', dest)
    return dest


@pytest.mark.parametrize('route', shadow.GATES)
def test_semantic_route_skips_and_records(isolated, route, monkeypatch):
    mod, name = route.rsplit('.', 1)
    obj = importlib.import_module('nrp_monitor.' + mod)
    def forbidden(*a, **k):
        pytest.fail('real side effect called')
    monkeypatch.setattr(obj, name, forbidden)
    with shadow.isolated_pass():
        getattr(obj, name)('fake')
    assert json.loads((isolated / 'shadow-actions.jsonl').read_text())['would_do'] == route


@pytest.mark.parametrize('verb', ['create', 'delete', 'patch', 'apply', 'replace', 'exec', 'label', 'annotate', 'wait', 'port-forward'])
def test_kubectl_disallowed_verbs_raise(isolated, verb):
    with shadow.isolated_pass(), pytest.raises(PermissionError):
        subprocess.run(['kubectl', '-n', 'fake', verb, 'job', 'fake'])
    assert 'kubectl ' + verb in (isolated / 'shadow-actions.jsonl').read_text()


@pytest.mark.parametrize('verb', ['get', 'describe', 'logs', 'top'])
def test_read_allowlist_uses_fake_cluster(isolated, monkeypatch, verb):
    calls = []
    def fake(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{}', '')
    monkeypatch.setattr(subprocess, 'run', fake)
    with shadow.isolated_pass():
        assert subprocess.run(['kubectl', '-n', 'fake', verb, 'pods']).returncode == 0
    assert len(calls) == 1


@pytest.mark.parametrize('argv', [['aws', 's3', 'cp', 'x', 's3://b/k'], ['claude'], ['codex'], ['agy'], ['curl'], ['sh', '-c', 'anything']])
def test_subprocess_writes_agents_and_shell_skipped(isolated, argv):
    with shadow.isolated_pass():
        assert subprocess.run(argv).returncode == 125
    assert 'subprocess' in (isolated / 'shadow-actions.jsonl').read_text()


def test_aliases_webhooks_network_and_external_writes(isolated, tmp_path):
    from nrp_monitor import agents, wake
    with shadow.isolated_pass():
        for fn in list(agents.RUNNER_EXEC.values()) + [agents.exec_claude, agents.exec_codex, agents.exec_agy]:
            assert fn()[0] == 'unavailable'
        for fn in wake.WAKE_EXEC.values():
            assert fn() is None
        with pytest.raises(PermissionError):
            urllib.request.urlopen(urllib.request.Request('https://example.com/webhook', data=b'no'))
        with pytest.raises(PermissionError):
            (tmp_path / 'outside').write_text('no')
        with pytest.raises(PermissionError):
            subprocess.Popen(['sh', '-c', 'true'])
        (isolated / 'allowed').write_text('yes')
    assert not (tmp_path / 'outside').exists()


def test_installed_state_refused(monkeypatch):
    monkeypatch.setattr(state, 'STATE', Path.home() / '.local/state/nrp-monitor')
    with pytest.raises(ValueError):
        with shadow.isolated_pass():
            pytest.fail('entered unsafe context')


def test_thanos_only_and_redirect_target_gated(isolated, monkeypatch):
    calls = []
    def fake_open(self, url, data=None, timeout=None):
        calls.append(url)
        return 'fake metrics'
    monkeypatch.setattr(urllib.request.OpenerDirector, 'open', fake_open)
    with shadow.isolated_pass():
        opener = urllib.request.build_opener()
        assert opener.open(state.THANOS_URL + '?query=fake') == 'fake metrics'
        with pytest.raises(PermissionError):
            opener.open('https://example.com/redirect-target')
        with pytest.raises(PermissionError):
            opener.open(urllib.request.Request(state.THANOS_URL, data=b'no'))
    assert len(calls) == 1


def test_gate_return_contracts(isolated):
    from nrp_monitor import agents
    with shadow.isolated_pass():
        assert agents.dispatch_agent().status == 'unavailable'
        assert isinstance(agents.run_agent(), str)


def test_filesystem_mutation_paths_are_gated(isolated, tmp_path):
    outside = tmp_path / 'keep'
    outside.write_text('original')
    with shadow.isolated_pass():
        with pytest.raises(PermissionError):
            outside.unlink()
        with pytest.raises(PermissionError):
            outside.rename(isolated / 'moved')
        with pytest.raises(PermissionError):
            (tmp_path / 'newdir').mkdir()
    assert outside.read_text() == 'original'
