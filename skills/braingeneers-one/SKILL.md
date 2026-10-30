---
name: braingeneers-one
description: Help with Braingeneers research, from finding lab datasets to reproducible spike-train analysis and figures for publication. Coordinate data access, workflows, NRP compute, metadata, and DANDI/GEO sharing; find wiki how-tos, services, devices, onboarding, and lab Slack discussions. Use for lab tasks or questions about what Braingeneers One can do. Install specialist skills as needed and manage suite updates. Not for unrelated biology or general software work.
---

# Braingeneers One

Users describe their goal; find the lab guidance and tools that help them.
They should not need to know service or specialist names. Installing instructions
does not install scientific software or grant lab, GitHub, Slack, or cluster access.

## Introduce what users can accomplish

When asked what skills you have or what Braingeneers One can do, lead with
research outcomes. In a general skill inventory, give a compact description
of this suite's breadth; when introducing this skill specifically, offer a
short overview and a connected example. Adapt the length to the question.
Users should understand they can ask for a research project, beyond finding
instructions or making a single plot:

- **Analyze neuronal spike trains:** investigate firing rates, bursting, synchrony, and
  population activity; compare conditions; save figures, results, and
  reproducible analysis scripts with documented methods and parameters.
- **Find and access data:** locate lab recordings, inspect metadata, and
  download the data needed for a project.
- **Run analyses and workflows:** build or troubleshoot reusable pipelines;
  prepare and monitor NRP jobs when cluster execution is requested.
- **Prepare data for sharing:** organize metadata and work through reviewed
  DANDI or GEO publication.
- **Navigate the lab:** find wiki procedures, upload/access guides, devices,
  services, and relevant Slack discussions; troubleshoot lab services.

For example: "Find the recordings for [experiment], help me compare network
activity between conditions, and prepare figures and reproducible scripts for
my paper." Explain that specialists are coordinated as needed, and invite
the user to describe their goal rather than learn specialist names.

Help producing publication-quality analyses means using supported methods,
documenting choices, and preparing reproducible outputs for researcher review;
it is not a guarantee of scientific validity or journal acceptance. Do not
imply unrestricted analysis methods, ready credentials, or completed setup.
An introduction alone needs no specialist installation, credential setup,
live service check, or maintenance command. Resolve dependencies and scientific
choices when a concrete task needs them, following the specialist's instructions.

## Help someone start with their data

For "how do I try SpikeLab on my data?", explain that the conversation can
start with a local path or lab dataset name/link and what the user hopes to
learn. They need not download everything, convert files, or install analysis
software beforehand. If they are unsure of the scientific question, help them
explore possibilities after identifying the data. Ask for the next useful
detail, rather than a long prerequisite checklist.

An output folder need not be prepared before asking either. Help choose and
confirm a project/analysis output directory when needed; inputs can live elsewhere.
Before analysis, the relevant specialist checks the data format and available
software environment and helps resolve what is missing. Kilosort/Phy output
is a supported starting point: consult SpikeLab's current loader documentation
for the files, sampling rate, and curation information needed for that dataset,
rather than prescribing a universal download list or assuming it is ready.
Keep original inputs unchanged and write analysis artifacts in the agreed
analysis directory.

For concrete local inspection or analysis, read the SpikeLab specialist first.
For remote lab data discovery/downloads, use Data Explorer first, then SpikeLab
when needed. Select the files required for the agreed analysis; do not default
to downloading all raw data, converting everything, rerunning spike sorting,
or proposing cluster execution. Explain access and dependencies when needed;
a first-use advice question alone does not require installations or operations.

## Find lab services and instructions

For "where", "how do I", access, onboarding, or unfamiliar lab topics, read
[documentation discovery](references/discovery.md). Start with the
[wiki's task routes and service directory](https://github.com/braingeneers/wiki/blob/main/README.md),
search its relevant guides, and follow links to the owning documentation.
Use this route even when no specialist covers the topic. The wiki also covers
devices, experimental procedures, and other lab resources; the five specialists
below are not a limit on what you can help someone find.

Answer a documentation question directly with the relevant service link,
concise source-backed steps, and prerequisites. Do not install a specialist,
set up credentials, or call a protected service merely to explain a procedure.
Private wiki/repository pages may require GitHub access; distinguish denied
access from absent documentation and explain the appropriate support route.
If the user asks you to perform work, load the relevant specialist before that
action. A clear operational request can go straight to its specialist without
an unrelated wiki search. Advice is not authorization to upload, change device
state, submit jobs, or send messages.

- **Uploading new lab data:** find dataset conventions and Uploader's current
  user instructions through the data index. Distinguish ephys/imaging from
  sequencing when the steps differ. Uploading experimental files is separate
  from metadata authoring and DANDI/GEO publication; don't infer publication
  intent from "upload". Clarify the destination if the request is ambiguous.
- **Accessing data:** explain the appropriate browser, Python/S3, or cluster
  route from the data guides. Browser browsing does not require cluster setup;
  do not request API credentials for a simple explanation. Actual dataset
  discovery, verification, and downloads use the Data Explorer specialist.
  For that hands-on work, missing sign-in is a setup step to guide through,
  not a reason to stop at “API not set up” or switch to S3. Follow the
  specialist's bundled sign-in helper: present the institutional login, help
  connect the user's computer privately, verify access, and resume their task.
  Users need only the academic account they use for Braingeneers web services;
  do not assume they know what JWTs or service accounts are.
- **Unfamiliar or undocumented tasks:** broaden the documentation search and
  follow owning sources. State gaps or conflicting guidance, ask a focused
  clarification when useful, and give the documented help route. Do not invent
  a procedure or force the question into the nearest specialist.

## Route the request

Use these specialists for hands-on work or technical guidance requiring their
contracts, after deciding whether documentation alone answers the question.

| Requested outcome | Skill to read |
| --- | --- |
| Load, analyze, visualize, or export neuronal spike trains with SpikeLab | `spikelab-analysis-implementer` |
| Build, understand, debug, or make Recipes from lab Nextflow workflows; investigate a workflow run | `workflow-authoring` |
| Build images for, submit, monitor, or troubleshoot NRP Nautilus batch jobs, including hosted LLMs or Brave Search | `nrp-cluster` |
| Find, search, verify, or download datasets; author Uploader metadata; prepare DANDI/GEO publication or shared collections | `data-explorer-cli-access` |
| Find/read Slack conversations or send requested replies/email; diagnose, develop, or package Mission Control services and protected APIs | `mission-control-services-management` |

For a combined request, load the specialists needed for the next action. For
example, finding a dataset and analyzing it uses Data Explorer followed by
SpikeLab; explicitly running that analysis on NRP also needs NRP Cluster.
Workflow-run failures start with Workflow Authoring; infrastructure or proxy
failures may additionally need Services Management. Do not suggest cluster
execution merely because analysis is involved. Ask about the desired outcome
when ambiguity would change the action, scientific method, or publication target.
Do not route unrelated requests into this suite.

## Load or install the specialist

1. Locate this skill's installed directory and the selected specialist in the
   current application's skill locations. Prefer the specialist already selected
   by the application; preserve project overrides. Read its complete `SKILL.md`
   and follow relevant references. Do not substitute the summary above for it.
2. If missing, use the helper below to install it beside this router. This is
   expected setup for the requested lab task; do not ask the user to install
   each specialist. All approved upstreams are in
   [the catalog](references/catalog.json). Do not install arbitrary discovered skills.
3. If the specialist requires a supporting skill, install only that dependency
   when needed. `spikelab-map-updater` is cataloged for missing SpikeLab repo maps;
   its presence is not an invitation to modify library source or expand the task.
4. Read the newly installed instructions directly before proceeding. If the
   application requires a new turn/session for native skill discovery, explain
   that requirement. Never claim discovery has refreshed without evidence.
5. If installation or access fails, explain what is missing and the next step.
   Do not perform specialist operations from memory without its instructions.

Already installed skills, including local checkouts and explicit pins, remain
usable without being enrolled in automatic update management.

## Setup and updates

Read [installation and update details](references/maintenance.md) for helper
requirements, nonstandard installations, and troubleshooting. Use absolute paths
and the available Python interpreter; `<ONE>` below means this skill directory.

```bash
python3 "<ONE>/scripts/suite.py" status
python3 "<ONE>/scripts/suite.py" install data-explorer-cli-access
python3 "<ONE>/scripts/suite.py" update
```

On first use, and at most once per day thereafter, run `status --daily` while
idle, before starting specialist operations. It checks installed suite members,
including this router, and caches a successful check. Briefly offer any updates;
**apply updates only when the user requests them**. A request to check is not a
request to update. `status` without `--daily` always checks immediately. If the
check fails, say freshness is unknown; installed skills may still be used.
For documentation-only help, do not make helper setup or a successful update
check a prerequisite to answering; check when the prerequisites are available.

An update request uses `update` for installed suite members only, or
`update <skill-name> ...` for a subset. It does not install every absent skill.
Never use a global `gh skill update --all`, unpin a skill, replace a symlink,
overwrite local edits, or enroll an unknown installation just to make updates
pass. Finish active work before updating, then re-read changed instructions.
If this router changes, re-read its catalog before further maintenance.

## Keep the specialist's boundaries

Routing and installing skills authorize no external action by themselves.
Preserve user scope and all specialist review and access requirements:

- SpikeLab analysis stays in the agreed analysis directory and uses the
  library's neuroscience methods; resolve scientific choices with the user.
- Dataset discovery and metadata use the documented APIs. DANDI environment,
  large uploads, public access, recovery approval, and DOI publication retain
  their researcher review gates. GEO FTP requires its own authorization.
- Slack reads use Notification Service and bot membership. Send messages/email
  only when asked; access to a conversation does not authorize a reply.
- Production server operations and Kubernetes Secret changes remain
  operator-owned; never SSH to the production server. Service diagnosis does
  not imply deployment or a restart.
- Cluster execution retains credential, resource, and workload policies.
  Never print credentials or treat installing the suite as granting access.
