import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.work = Path(self.temp.name) / 'work'
        for rel, text in {'pkg/__init__.py': '', 'pkg/a/__init__.py': '',
                          'pkg/b/__init__.py': '', 'pkg/a/core.py': 'def value():\n    return 1\n',
                          'web/main.js': 'export const value = 1;\n',
                          'figures/panel.py': 'print("panel")\n'}.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'fixture'], check=True)

    def call(self, script, *args, rc=0, env=None):
        result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], cwd=self.root,
                                capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, rc, result.stdout + result.stderr)
        return result

    def annotate(self):
        for batch in (self.work / 'batches').glob('*.json'):
            data = json.loads(batch.read_text())
            out = self.work / 'out' / batch.name
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps({f['path']: dict(source_sha256=f['sha256'], overview='Concrete fixture overview.',
                config=[], data_shapes=[], notes=[], connections=[]) for f in data['files']}))
            self.call('validate_batch.py', batch, out)

    def test_default_end_to_end(self):
        plan = json.loads(self.call('summaries.py', 'plan', '--json').stdout)
        self.assertEqual(plan['count'], 3)
        self.assertEqual(plan['tiers'], {'full': 2, 'brief': 1})
        self.assertEqual(plan['feature_areas']['pkg/a/core.py'], 'pkg/a')
        self.call('make_batches.py', self.work)
        self.annotate()
        self.call('summaries.py', 'build', '--annotations', *sorted((self.work / 'out').glob('*.json')))
        self.call('summaries.py', 'check')
        path = self.root / 'pkg/a/core.py'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        self.call('summaries.py', 'check')
        path.write_text('def value():\n    return 2\n')
        self.call('summaries.py', 'check', rc=1)

    def test_configuration(self):
        (self.root / '.code-summaries.json').write_text(json.dumps({'areas': {'pkg/': ['Package', 'Flow'], 'pkg/a/': ['Core', 'Core flow']},
            'brief_dirs': ['web'], 'skipped_dirs': ['figures']}))
        plan = json.loads(self.call('summaries.py', 'plan', '--root', self.root, '--json').stdout)
        self.assertEqual(plan['count'], 2)
        self.assertEqual(plan['feature_areas']['pkg/a/core.py'], 'Core')
        self.assertEqual(plan['tiers'], {'full': 1, 'brief': 1})

    def test_resume_and_validation(self):
        env = dict(os.environ, WORK=str(self.work))
        self.call('refresh.py', '--all', rc=1, env=env)
        self.assertTrue((self.work / 'PROMPT.md').exists())
        self.annotate()
        batch = next((self.work / 'batches').glob('*.json'))
        out = self.work / 'out' / batch.name
        saved = out.read_text()
        data = json.loads(saved)
        next(iter(data.values()))['source_sha256'] = 'wrong'
        out.write_text(json.dumps(data))
        self.call('validate_batch.py', batch, out, rc=1)
        out.write_text(saved)
        self.call('refresh.py', env=env)
        self.call('summaries.py', 'check')

    def test_cli_quota_and_timeout(self):
        env = dict(os.environ, WORK=str(self.work), ANNOTATOR_CMD='exit 10', PARALLEL='1')
        self.call('refresh.py', rc=1, env=env)
        self.assertTrue((self.work / 'QUOTA_OUT').exists())
        self.assertFalse((self.root / '.code-summaries').exists())
        env.update(ANNOTATOR_CMD='sleep 1', ANNOTATOR_TIMEOUT='0.01')
        self.call('refresh.py', rc=1, env=env)
        self.assertTrue(any('TIMEOUT' in p.read_text() for p in (self.work / 'logs').glob('*.log')))
        self.annotate()
        self.call('refresh.py', env=dict(os.environ, WORK=str(self.work)))

    def test_cli_annotation(self):
        wrapper = Path(self.temp.name) / 'annotate.py'
        wrapper.write_text('import json,os,sys\nfrom pathlib import Path\nb=Path(sys.argv[1]); d=json.loads(b.read_text()); '\
            'out={f["path"]:dict(source_sha256=f["sha256"],overview="CLI fixture",config=[],data_shapes=[],notes=[],connections=[]) for f in d["files"]}; '\
            '(Path(os.environ["WORK"])/"out"/b.name).write_text(json.dumps(out))\n')
        env = dict(os.environ, WORK=str(self.work), ANNOTATOR_CMD=f'"{sys.executable}" "{wrapper}" "$1"', PARALLEL='2')
        self.call('refresh.py', env=env)
        self.call('summaries.py', 'check')


if __name__ == '__main__':
    unittest.main()
