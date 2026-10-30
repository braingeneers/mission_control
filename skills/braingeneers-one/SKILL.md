---
name: braingeneers-one
description: Help with Braingeneers lab tasks by selecting and installing the lab's specialist skills for spike-train analysis, Nextflow workflows, NRP cluster jobs, data discovery and publication, or lab services and Slack. Also check and update the Braingeneers skill suite. Use for these lab tasks, not unrelated biology or general software work.
---

# Braingeneers One

Users describe their goal; you select the lab guidance. They should not need to
know specialist names or manage their installations. Installing instructions
does not install scientific software or grant lab, GitHub, Slack, or cluster access.

## Route the request

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
