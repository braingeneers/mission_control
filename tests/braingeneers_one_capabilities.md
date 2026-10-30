# Braingeneers One capability-introduction review

Evaluate what a new user learns from the skill, not whether an answer repeats
particular wording. Give independent evaluators the question and relevant raw
skill/setup sources before showing this rubric. Keep checks read-only: no lab
operations, specialist installation, or changes to real user skills/settings.

## Scenarios

| Context and question | Acceptance |
| --- | --- |
| Only the skill's name and description are supplied: “what skills have you?” | Communicates that the suite can help with research analysis and figures as well as lab guidance, data, compute/workflows, and sharing. This checks discovery metadata, not native application discovery. |
| Fresh application session: “What can Braingeneers One help me accomplish?” | Describes concrete outcomes across the suite and a connected research example, without making users learn specialist names or initiating setup/operations. |
| “Use Braingeneers One. I want to find recordings for my experiment, compare network activity between conditions, and prepare figures and reproducible scripts for my paper. What do you need from me before we start? Do not access data, install anything, or run jobs yet.” | Recognizes a combined research project; asks for experiment/data identifiers, scientific comparisons, and output/workspace needs without inventing methods or silently choosing scope. Does not start operations or prescribe cluster execution. |
| Setup completion fixture: installation/source/freshness and app discovery confirmed, private wiki retrieval denied with 404 | Distinguishes installed skill from pending documentation access; explains research potential, offers a connected example and the existing read-only first question, and gives the lab support route without reinstalling or repeating login. Fixture facts do not establish an actual installation or access check. |

## Claim review: 2026-10-30

Checked the advertised outcomes against the owning specialist instructions and
local library source:

- SpikeLab supplies firing-rate, burst, STTC synchrony, and population-activity
  methods. Its analysis skill supports condition comparisons through library
  outputs, self-contained scripts, saved workspaces, figures, parameter
  documentation, and an analysis log. Scientific choices remain researcher-led.
- Data Explorer supports dataset search, metadata inspection, and downloads;
  its publication references retain DANDI/GEO review and human submission steps.
- Workflow Authoring and NRP Cluster cover reusable workflows, run diagnosis,
  requested job execution, and monitoring. Services Management and the router's
  discovery reference cover lab services, wiki procedures, and Slack discussions.

These are supported capabilities, not evidence of credentials, software setup,
live service health, completed scientific analysis, or journal acceptance.
Analysis examples concern neuronal spike trains, not arbitrary biological data
or an additional spike-sorting skill outside the router's catalog.

## Validation evidence

Four independent fresh-agent scenarios were run with the inputs above and no
expected-answer rubric. Each met the behavior-level acceptance criteria:

- Description only: named research analysis and publication figures alongside
  data, workflows/compute, sharing, and lab guidance without reading the body.
- Full skill: gave five outcome groups, a connected experiment-to-paper example,
  and the software/access distinction without installing anything or reading
  specialist instructions.
- Research handoff: asked for experiment identifiers, scientific comparisons,
  replicate structure, data readiness, and deliverables/workspace. It did not
  select methods or start operations.
- Setup fixture: reported documentation access pending separately from installed
  skill status, introduced the research possibilities, gave the example and
  read-only upload-guide request, and pointed to the helpdesk. It performed no
  access check itself.

These were fresh Codex subagents, not native application discovery tests.
Claude Code 2.1.86 was also attempted with isolated home/configuration and a
temporary credential copy, no hooks/plugins/MCP, and restricted tools. All four
cases stopped at HTTP 401 (invalid OAuth access token), with zero model input/
output tokens and no tool calls. Its initialized default was
`claude-sonnet-4-6`, with no model override. The temporary project skill was
also absent from initialization's skill list with empty setting sources, so
that isolation configuration was not proven to support native discovery.
Consequently no successful Claude behavior or native skill-discovery result is
claimed; user authentication and installed skills were not changed. Raw attempts were saved locally under
`/tmp/braingeneers-one-claude-eval-r7dit68_`.

The skill validator passed. GitHub-style and Jekyll previews passed at 1280px
and 390px, with visual inspection, 16 existing anchors preserved, unchanged
manual installation commands, and working setup navigation. Preview results:
`/tmp/wiki-restructure-preview/capabilities-results.json`.

Reused the 19 passing helper tests recorded at `5577887`: comparison confirmed
that `suite.py`, its tests, and the catalog are unchanged. No helper dependency
or configuration change is included. Those runtime tests do not establish the
new introductory behavior; the independent responses above cover that change.

## First-analysis review: 2026-10-30

Ran independent fresh-agent, advice-only cases with the revised router as the
only source. Input paths and identifiers were fictional; no data inspection,
software/skill installation, maintenance, or service access was permitted.
Evaluators received the questions, not this acceptance rubric.

| User starting point | Observed response and acceptance |
| --- | --- |
| Local Kilosort/Phy output; asks whether to install SpikeLab, convert files, or copy them into a Claude folder first | Said files can stay where they are and preparation is not required before asking. Offered a goal/path-based prompt, specialist-led file/environment checks, and an example output directory while preserving inputs. No universal file list or claimed analysis readiness. |
| Lab-hosted dataset name only; asks whether to download everything and create a folder first; unsure what to analyze | Said the name is enough to begin locating data; described Data Explorer discovery followed by selecting needed files and SpikeLab analysis. Asked for a useful identifying detail. Did not download anything, prescribe cluster execution, or choose an analysis without the user. |
| Unknown `.npy`/`.h5` files; asks what to prepare | Distinguished file extensions from actual data content, started with path and goal, and deferred format/software/output-directory checks to specialist-led work. Did not assume the files were sorted spikes or start sorting/conversion. |

The first unknown-format response suggested having an output folder ready.
Clarified explicitly that a pre-created output folder is not required before
asking, then reran that case with a new independent agent. Its answer began
with the folder path and scientific interest and offered to help choose the
output directory later. Local/remote cases had already made this distinction.

These checks validate first-response guidance, not successful loading of a
particular dataset, an installed SpikeLab environment, or native Claude Code
behavior. The Kilosort/Phy support claim was separately checked against
`load_spikedata_from_kilosort` in SpikeLab's current loader source; actual
requirements must still be checked for the user's installed version and data.
The helper, catalog, installation commands, and update policy are unchanged.

Skill validation passed. The changed wiki page rendered in Jekyll and
GitHub-style previews at desktop/mobile widths, preserving all 16 existing
anchors and manual install commands; setup navigation still passed. Results:
`/tmp/wiki-restructure-preview/first-analysis-results.json`.
