# Help a user install Braingeneers One

**For the agent:** read this guide, handle the commands you can, and explain the
human steps as they arise. The user should not need to understand Git protocols,
choose a skill directory, or install each specialist. This guide is public and
can be read before the skill or GitHub CLI is installed. If necessary, fetch
[the raw guide](https://raw.githubusercontent.com/braingeneers/mission_control/main/docs/braingeneers-one-setup.md)
with browsing or an HTTPS download tool.

The normal result is one new user-scoped skill, `braingeneers-one`, with its
upstream source recorded. Preserve existing skills, authentication, SSH keys,
and project settings. Installation does not grant lab access or authorize lab
operations. No repository clone or SSH key is required for the normal route.

## 1. Identify the application and environment

Determine the current assistant and operating system from available context.
If the application is unclear, ask which one the user is using. Install in the
environment where that assistant runs, including the correct home directory.

If you cannot run local commands, say so. Give the user the exact command and
explain expected prompts one step at a time; resume after their result. Do not
claim to have installed or verified something you could not check.

## 2. Check GitHub CLI

Run these checks; a version number alone does not prove skill support:

```bash
gh --version
gh skill install --help
```

If missing or unsupported, follow the [official GitHub CLI installation options](https://cli.github.com/)
for the user's platform. Reuse their existing package manager when appropriate
(for example, Homebrew on macOS or WinGet on Windows). Help install or update
GitHub CLI within the environment's normal permissions; do not silently install
another package manager, upgrade unrelated packages, or bypass managed-computer
restrictions. If a human or IT administrator must perform a step, provide the
specific command or request and wait for its result.

## 3. Reuse authentication or guide sign-in

Check the active account without displaying credentials:

```bash
gh auth status --active --hostname github.com
```

If it works, continue without logging in again. Preserve working HTTPS or SSH
settings. If authentication needs setup, check for an existing preference with
`gh config get git_protocol --host github.com`; an unset value is normal.

For fresh setup with no existing preference, use browser login and **HTTPS**:

```bash
gh auth login --hostname github.com --git-protocol https --web
```

These flags choose the host, protocol, and browser flow. If a protocol question
still appears during fresh setup, choose **HTTPS**. If asked to authenticate Git
with GitHub credentials, explain that this configures Git access; for a fresh
setup, accept it. Preserve an existing Git authentication setup instead of
changing it as an incidental part of skill installation.

Tell the user what to do before waiting: open the GitHub URL supplied by the
running command, enter its one-time device code if requested, sign in, and
approve the GitHub CLI request. The user completes sign-in in the browser;
never ask them to send a password, private key, or access token. Do not run
`gh auth token` or use `--show-token` to troubleshoot this flow.

Keep the same live login process while the user authenticates when your tools
support it. Do not start repeated logins while one is waiting. If you cannot
maintain an interactive process, have the user run the exact login command in
their terminal and report when it finishes. Recheck authentication afterward;
if it failed, explain the actual error and next step before continuing.

For an existing SSH preference, retain it; browser login can use
`--git-protocol ssh --skip-ssh-key` in place of `--git-protocol https` without
creating keys. Only help create or register SSH keys if the user explicitly
requests SSH setup or their environment requires it. Follow
[GitHub's SSH setup guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh),
reuse suitable existing keys, and never overwrite or expose a private key.

References: [login options](https://cli.github.com/manual/gh_auth_login),
[authentication status](https://cli.github.com/manual/gh_auth_status).

## 4. Install for the correct assistant

Use the matching identifier and user scope explicitly. The defaults may select
a different assistant or install only into the current project.

| Assistant | `AGENT` value | Usual skill directory under the user's home |
| --- | --- | --- |
| Codex | `codex` | `.codex/skills` |
| Claude Code | `claude-code` | `.claude/skills` |
| GitHub Copilot | `github-copilot` | `.copilot/skills` |
| Gemini CLI | `gemini-cli` | `.gemini/skills` |
| Cursor | `cursor` | `.cursor/skills` |

Replace `AGENT` below with that identifier, then run:

```bash
gh skill install braingeneers/mission_control braingeneers-one@main --agent AGENT --scope user
```

For the reported Claude Code case, `AGENT` is `claude-code`. Read the resulting
installation path; actual application configuration and CLI output take
precedence over the usual directories above. Check for an existing skill first.
If present, inspect it and use its maintenance instructions rather than forcing
a replacement. Preserve pins, local edits, symlinks, unrelated skills, and
project overrides. Do not install the whole repository's skill catalog.

See [GitHub CLI's skill installation reference](https://cli.github.com/manual/gh_skill_install).

## 5. Verify the installed copy

Read `SKILL.md` at the reported installation path. Confirm its name is
`braingeneers-one`, and its injected GitHub metadata identifies
`braingeneers/mission_control`, source path `skills/braingeneers-one`, and an
upstream Git tree hash. Do not treat command success alone as proof of placement.

Use an available Python 3.8+ interpreter with PyYAML. Check the interpreter you
will actually use with `import yaml`; `python` and `python3` may be different
environments. If needed, prepare a suitable environment using the installed
[maintenance instructions](../skills/braingeneers-one/references/maintenance.md#requirements).
Use a virtual environment outside the skill directory when system Python is
managed. Do not bypass its package policy or change the user's default Python.

Run the installed helper, substituting the actual interpreter and path:

```bash
python3 "<installed-skill-directory>/scripts/suite.py" status
```

It verifies source integrity and freshness. A fresh router-only installation
should report Braingeneers One current and specialists not installed. A previous
installation can legitimately have specialists present; do not remove them.
Report unknown freshness, skipped checks, or missing helper prerequisites
accurately, and distinguish these from whether the skill's files are installed.
Do not install specialists merely to make a setup check pass.

## 6. Confirm discovery and give the user a first question

Check the selected application's official skill-discovery instructions if it
does not recognize the new skill. Explain any required refresh or new session;
files on disk do not prove the current conversation has loaded them. The
[wiki's setup page](https://github.com/braingeneers/wiki/blob/main/shared/agent_skills.md#using-skills)
links the application-specific guides; consult the application's public docs
directly if the user cannot read the private wiki.

Summarize the installed application/path, source, verification result, and any
remaining dependency or access step. Then read the installed skill's
**Introduce what users can accomplish** section and give a brief introduction
to the research outcomes available: finding lab data, analyzing recordings with
reproducible scripts and figures for publication, running workflows or requested
cluster jobs, preparing data for sharing, and finding lab guidance. Include
one connected research example and invite the user to describe their goal.
Do not install specialists or start lab operations just to demonstrate breadth.

For an easy first check, also offer this read-only request:

> Use Braingeneers One to find the lab instructions for uploading a new recording. Give me the relevant guide links; do not upload anything.

If the user wants to try an analysis instead, offer this alternative:

> Use Braingeneers One to help me try SpikeLab on my data at [folder or dataset link]. Help me check what's available, set up an analysis folder, and understand which analyses fit my question before running them.

They can start with the data's current location and their goal; downloading all
data, converting formats, and installing SpikeLab are not prerequisites to
asking. Follow the installed skill's **Help someone start with their data**
guidance to resolve the actual analysis requirements progressively.

For the upload-guide request, expect links to dataset conventions and Uploader
instructions. Some lab repositories, including the wiki, require Braingeneers
GitHub access. A
404 may indicate denied access. Report **skill installed; documentation access
pending** when appropriate; do not keep reinstalling, changing accounts, or
logging in again to solve organization membership. Direct the user to
`#braingeneers-helpdesk` on UCSC GI Slack for lab access assistance.
