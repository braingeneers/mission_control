# Braingeneers first-use sign-in validation

Validated October 30, 2026. All automated credentials were synthetic; no real
credential files, institutional login, or protected services were used.

## Behavioral evaluations

Independent agents read the router and specialist instructions, with no desired
answer supplied. Tests simulated service responses rather than calling them.

- **Baseline:** “Help me find our recent electrophysiology datasets,” no saved
  credential or braingeneerspy. The old guidance produced an instruction to save
  JSON with restricted permissions, leaving novice file setup unexplained.
- **Revised first use:** same request, no browser control and no user input into
  agent terminals. The agent gave the exact bundled-helper command for a
  user-accessible terminal, institutional login link, hidden paste instructions,
  and continuation after an authenticated `/api/sources` check.
- **Existing package sign-in:** the agent reused the selected package credential
  without login, installation, or an unnecessary move to `~/.ssh`.
- **Fresh credential rejected:** a simulated 403 stopped the search and directed
  the user to documented access help, without a login loop or sending messages.
- **Explanation only:** “How do I browse datasets on the website?” received the
  website link and browsing steps without local credential setup.
- **Remote environment:** the first pass found that a laptop terminal may not
  share the agent's filesystem. After repair, the agent required a shared
  environment or supported private file transfer and an agent-side check.

## Helper checks and review

Both repositories run `python3 -m unittest discover -s tests -p
'test_skill_authenticate.py'`. The 13 tests cover discovery/selection, embedded
expiry, import, file permissions, atomic replacement and failure preservation,
cancellation, sanitized output, noninteractive refusal, browser failure, and
real POSIX terminal input with formatted JSON and lines longer than 4 KiB.
The 19 existing router-helper tests and all three skill validators passed.

The independent privacy reviewer reproduced an early-paste leak during browser
startup. Private terminal mode now precedes both the paste invitation and browser
launch. A delayed-browser PTY regression and the reviewer's original reproduction
both verified the repair: no credential echo, successful save, restored settings.

The identical helper in Data Explorer is a standalone distribution copy of
`skills/mission-control-services-management/scripts/authenticate.py`. Change
that maintained source, copy it and its tests to the Data Explorer repository,
run the focused tests in each repository, and compare helper bytes before delivery.

Live institutional sign-in/API acceptance, Windows console behavior, and private
browser capture in individual agent clients were not verified. Browser capture
is explicitly conditional in the guidance; terminal paste is the tested fallback.
