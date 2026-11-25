# Installation and maintenance

## Requirements

The helper needs Python 3.8+ and GitHub CLI with `gh skill install`
(2.90.0+; currently preview). Check `gh skill install --help` rather than assuming
a version number alone proves support. The YAML reader is bundled with the
skill; no pip, separate Python packages, virtual environment, or compiler is
needed. Its version, source checksum, license, and refresh procedure are recorded
in [the bundled reader notice](../scripts/_vendor/PyYAML-NOTICE.md).

Check the interpreter that will run the helper with `--version`. On macOS and
Linux, try `python3`; on Windows, try `py -3` or `python`. Use whichever available
command reports Python 3.8 or later, and quote script paths containing spaces.
Do not change the user's default Python. If no suitable interpreter is
available, help install Python through the environment's normal setup process
within the user's permissions. Do not use `sudo` or bypass managed-machine
policy. Missing Python or GitHub CLI does not prevent reading the instructions.

Older installed helpers may still require external PyYAML. To upgrade one,
use an existing compatible Python environment, or run the new self-contained
helper from a verified upstream download with the installed `--skills-dir`
explicitly selected. Preserve the normal source, local-edit, pin, and symlink
checks; do not force replacement to get past an old prerequisite failure.

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

For Claude Code and Codex, bootstrap the router in `~/.claude/skills/`.
When managing that root, `install` and `update` make each selected installed
skill available to Codex through a link in
[`~/.agents/skills/`](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).
Existing filesystem entries are preserved. For an existing direct install
elsewhere, continue maintaining it in its own root.

Common user locations for other hosts are `~/.copilot/skills`,
`~/.gemini/skills`, and `~/.cursor/skills`. Actual application configuration
takes precedence over these examples.

## Helper behavior

- `status --table` lists local entries and absent catalog members with their
  installation mode, source, update state, and Codex link status. `status --json`
  gives the same fields in JSON, which is also the default. Both omit Claude's
  `synced/` directory. `--daily` reuses a recent check when local entries are
  unchanged. Network failures are reported per member. Failed
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
  A pristine installation made by GitHub CLI becomes managed once verified.
  Explicit pins and symlinks remain under their owners' control. Maintainers
  can link an installed skill name to a live Git checkout, then pull updates
  in that checkout. If a link is dangling, restore its target or repair it.
- A modified managed copy is **stuck** because future updates preserve its
  edits. `reset NAME` moves it to a timestamped backup under the state
  directory and reinstalls the catalog version. The output gives the backup
  path and a diff summary listing files added, modified, or removed since the
  last managed installation. Review the backup to recover or upstream edits.
- Downloads are staged and verified before replacement. Failed downloads leave
  the installed skill intact. Regular update backups are retained beside the skills
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
Translate helper results into the plain-language messages described in SKILL.md;
structured statuses and technical reasons are diagnostics for the agent, not
text to paste into the answer. Explain any necessary next step, preserve the
installation, and offer the appropriate owner-managed update
(for example, reviewing changes and pulling a clean symlinked checkout).
Do not use force or clear a pin to silence a warning.

## Opt in to daily updates

Use the installed router to run the following commands.

```bash
python3 "<ONE>/scripts/suite.py" schedule enable
python3 "<ONE>/scripts/suite.py" schedule status
python3 "<ONE>/scripts/suite.py" schedule disable
```

The per-user job runs daily at 9 a.m. local time. On macOS a LaunchAgent runs
in the user's login session. On Linux a systemd user timer runs when the user
manager is available. If systemd is unavailable, `schedule enable` prints a
line to add with `crontab -e`. Manage that entry directly with `crontab -l` and
`crontab -e`.

The job runs `update --auto`, which updates only recorded, unmodified managed
copies. Run `status` once after a new setup so it can verify and record any
pristine GitHub CLI installs. After enrollment, each managed copy follows its
own source repository. Codex links see the same installed files as Claude.
The job is quiet when no copy changes and prints the skill names when it
updates them. Check `auto-errors.log` in the state directory on macOS or
`journalctl --user -u org.braingeneers.one-update.service` on Linux for errors.
The job uses the Python interpreter and executable search path available at
enable time. Set up GitHub CLI sign-in that works without an interactive prompt
before enabling it.
