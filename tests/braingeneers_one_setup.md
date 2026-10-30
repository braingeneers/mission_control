# Braingeneers One setup review

Review the public setup guide with these starting conditions. Judge the action
and verified result, not exact response wording. Preserve the user's real
accounts, keys, installed skills, and project settings during evaluation.

## Review: 2026-10-30

| Starting condition | Expected agent behavior | Evidence |
| --- | --- | --- |
| Fresh Claude Code setup on macOS, as reported by a lab user | Check CLI support; select `claude-code` and user scope; use HTTPS/browser login for a fresh account configuration; explain the remaining Git-credentials question and browser approval. | Guide reviewed against the reported prompt and CLI help. Equivalent fresh-login flags exercised with the real CLI in an isolated Linux terminal; macOS/browser completion not claimed. |
| Working HTTPS authentication | Reuse the active login; do not run login again. | Existing active-account status checked successfully without changing authentication. |
| Existing SSH preference | Preserve the preference; if login needs setup, select SSH with `--skip-ssh-key` and browser login. | Isolated CLI run preserved the effective SSH preference and created no SSH directory or keys. |
| Missing GitHub CLI | Help install it using official platform instructions and an appropriate existing package manager, within available permissions. | Decision walkthrough; no package manager or system installation performed. |
| CLI lacks `gh skill install` | Detect failure of the capability check and help update the CLI; do not infer support from a version alone. | Guide/capability-check review; the current CLI supports the required agent and scope options. |
| Python environment lacks PyYAML | Check the actual interpreter; use another compatible environment or prepare an appropriate environment outside the skill directory. | The workstation's available interpreters differ; existing compatible Python was identified without changing default Python or managed packages. |
| Agent cannot execute commands | Explain the limitation, supply exact commands and expected choices one step at a time, and wait for the user's results. | Decision walkthrough; no claim of unattended installation. |
| Private wiki access denied after skill installation | Report installed skill separately from pending organization access; provide the helpdesk route without repeated logins or reinstalling. | Guide review against previously confirmed private-wiki behavior; public-guide availability checked separately during publication. |
| Existing skill, local edits, pin, or symlink | Inspect and follow maintenance guidance; preserve the installation rather than forcing replacement or removing other skills. | Decision walkthrough. Existing suite preservation checks remain applicable because helper code, tests, and catalog are unchanged. |

## Interactive login check

Used GitHub CLI 2.91 with a pseudo-terminal, isolated home/configuration/Git
settings, and a local HTTPS proxy that deliberately rejects authentication
requests. Cleared authentication environment variables for those subprocesses.

- Fresh HTTPS flags removed the protocol choice and SSH-key setup prompts.
- The remaining Git-credentials prompt was answered for the fresh test profile.
- SSH browser-login flags with `--skip-ssh-key` removed key setup prompts and
  preserved the effective SSH preference. GitHub CLI's own config-version
  bookkeeping is not treated as a protocol change.
- Both runs reached the expected browser-authentication network request and
  stopped at the intentional proxy error. Exit failure here is expected; this
  does **not** establish completed browser/OAuth authentication.
- No real account was logged out or changed, and no SSH keys were generated.

Publication checks must also confirm anonymous retrieval of the public guide
before the wiki links to it, a real isolated Claude Code user-scope download,
installed-source verification through `suite.py status`, and wiki rendering.
These checks do not substitute for observing a newcomer complete browser sign-in
on their own computer.
