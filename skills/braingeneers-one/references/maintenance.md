# Installation and maintenance

## Requirements

The helper needs Python 3.8+, PyYAML, and GitHub CLI with `gh skill install`
(2.90.0+; currently preview). Check `gh skill install --help` rather than assuming
a version number alone proves support. If `import yaml` fails, install PyYAML in
the interpreter/environment used for the helper, for example
`python3 -m pip install --user PyYAML`, or use a virtual environment when required
by the operating system. Explain a missing prerequisite and help the user set
it up within their permissions. Do not use `sudo` or bypass managed Python policy.

For initial installation or GitHub sign-in problems, follow the public
[agent setup guide](https://github.com/braingeneers/mission_control/blob/main/docs/braingeneers-one-setup.md).
It covers environment checks, preserving working authentication, HTTPS for
fresh browser login, and human sign-in steps. SSH keys are not a prerequisite
for the normal installation route. Lab API credentials and SpikeLab/cluster
software are separate prerequisites; follow the selected specialist when those
become necessary.

## Placement

Run `python3 <ONE>/scripts/suite.py <operation>` from anywhere. By default,
the installation root is the parent of this router directory, so specialists
share its application and scope. An explicit `--skills-dir /absolute/path`
overrides that root. Use this for a symlinked router whose resolved source lives
outside the application's skill directory, or a development checkout. Do not
install specialists into a source repository accidentally. If the skill is
already available at a different application-recognized location, read it there
instead of installing a duplicate. Use its containing directory with
`--skills-dir` if the user requests maintenance there.

Common user locations are `~/.codex/skills`, `~/.claude/skills`,
`~/.copilot/skills`, `~/.gemini/skills`, and `~/.cursor/skills`. Project installs
use `.agents/skills` for these apps except Claude Code's `.claude/skills`.
Actual application configuration takes precedence over these examples.

## Helper behavior

- `status [--daily]` checks installed catalog members against their own `main`
  branch. Missing members are listed, not installed. Network failure is reported
  per member; a partial result never records a successful daily check. Failed
  daily attempts are throttled for one hour to avoid repeated offline checks;
  an explicit `status` always retries. A cached check is labeled with its time.
- `install NAME` installs just a missing catalog member. Existing directories,
  pins, and symlinks are not overwritten. The support entry is used only when
  a specialist requires it.
- `update [NAME ...]` updates installed members after the user's request.
  Specialists update first, this router last. Missing members remain absent.
- Status verifies unknown installations with GitHub source metadata against
  their original immutable Git tree, including every file, before recording a
  local fingerprint. Source/path mismatch, unsupported objects, missing or
  changed files, added files, or changed instructions prevent enrollment.
  Explicit pins and symlinks are skipped. The helper does not repair these
  installations automatically.
- Downloads are staged and verified before replacement. Failed downloads leave
  the installed skill intact. Previous versions are retained beside the skills
  root in `.braingeneers-one-backups/`; the helper reports their location. They are not
  automatically restored over subsequent local work.
- Local state and fingerprints live under
  `~/.cache/braingeneers-one/<installation-root-id>/state.json`, or
  `$XDG_CACHE_HOME/braingeneers-one/...`. The file contains no credentials.
  `--state-dir` selects another location. One helper per root/state pair runs at a
  time; use the same state directory for that root. If interrupted, verify the
  process has stopped before using `trash` on the reported `running.lock` directory.

GitHub CLI's injected source metadata supplies provenance. The helper checks
the catalog branch explicitly with `gh api`, then downloads the resolved commit
with `gh skill install`. This avoids the repository-wide latest-release
selection in the inspected GitHub CLI 2.91 updater, which can select an
application release unrelated to the skill. It also avoids updating unrelated
skills or relying on terminal output parsing. See
[installation](https://cli.github.com/manual/gh_skill_install) and
[updates](https://cli.github.com/manual/gh_skill_update).

If a local installation is skipped, it remains readable for the requested task.
Explain the reason, preserve it, and offer the appropriate owner-managed update
(for example, reviewing changes and pulling a clean symlinked checkout).
Do not use force or clear a pin to silence a warning. No automatic background
job or scheduled updater is created.
