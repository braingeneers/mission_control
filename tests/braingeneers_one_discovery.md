# Braingeneers One documentation-discovery review

Use these user questions to review discovery behavior after routing changes.
Give an evaluator the question and installed skill before showing the expected
outcome. Check the retrieved source and the answer's scope, not exact wording.
Use read-only access; these questions do not authorize uploads, jobs, messages,
device control, or publication. Hands-on examples below test the handoff only.

## Read-only walkthrough: 2026-10-30

Reviewed the revised router/reference against the local wiki and upstream
`main` sources. Retrieved the remote wiki home, data index, permissions guide,
and Uploader README through GitHub's contents API. This was a documentation and
decision walkthrough, not an independent model evaluation or interactive test
of each supported agent application.

| User question | Source followed and expected outcome | Walkthrough |
| --- | --- | --- |
| Where can I view live recordings? | Wiki `README.md`, Service Directory: identify NeuroView and its Docs link; provide navigation without claiming the service was tested live. | Directory route and source link found. |
| How do I upload a new recording? | Wiki `api_data/index.md` → `organizing-data.md` → Uploader README, Workflow. Explain lab upload; do not infer DANDI publication or start an upload. | Linked instructions retrieved upstream. |
| How do I upload a provider's FASTQ delivery? | Data index → sequencing layout → Uploader README, Sequencing Uploads. File upload and later GEO metadata/publication remain separate. | Dedicated sequencing instructions retrieved upstream. |
| Can I access data without a cluster account? | `api_data/data-explorer.md` and `shared/permissions.md`: browser route and applicable sign-in; no local S3 keys or Kubernetes setup for browsing. | Both guides explicitly support this distinction. |
| How do I read our data from Python? | Data index → Python tools and `api_data/s3-reference.md`; distinguish individual S3 access from web-service JWTs and cluster credentials. | Python and credential routes found; no credentials retrieved. |
| I'm new. How do I get access? | `shared/onboarding.md` → `shared/permissions.md`; identify the relevant access category and documented helpdesk route. | Onboarding, access categories, and support route found. |
| Where is the Picroscope control console? | Wiki Service Directory: provide the Picroscope Console link; navigation does not authorize operating the device. | Console link found. |
| What does the pump ASPIRATE command do? | Wiki IoT Devices → `shared/device_specifc_commands.md`; read the relevant model/command section, clarify model if needed, send no command. | Pump command reference found beyond the five specialist areas. |
| Where are the instructions for curating sorted spikes with Phy? | Wiki Ephys → `ephys/Curation_SOP.md`; give the procedure link and relevant explanation without forcing a SpikeLab analysis workflow. | Scientific procedure found outside specialist routing. |
| What is the lab's blue-orchid-vortex calibration protocol? | Search indexes and the wiki for the name and synonyms; no documented match means ask for context and link support, with no invented operating parameters. | No matching wiki procedure found; treat as a documentation gap, not a protocol to improvise. |
| I installed the skill, but the wiki returns 404. | Distinguish installation from GitHub access; explain that a private repository may return 404 without permission, use an authorized checkout/session if available, and give the helpdesk route. | Unauthenticated raw wiki retrieval returned 404; authenticated repository metadata confirmed the wiki is private, and authenticated contents requests succeeded. |
| Find and download one recording for this experiment. | This asks for an operation: load `data-explorer-cli-access` before authenticated dataset discovery/downloads; do not stop at a how-to or call protected APIs from router summaries. | Specialist handoff reviewed; no dataset/API operation executed. |

## Retrieval and packaging checks

- The discovery reference supplies a remote route when no local wiki checkout
  exists. The wiki and Uploader repositories were confirmed private; GitHub
  access is distinct from lab API credentials. An unauthenticated raw wiki
  request failed with 404, so do not claim anonymous wiki retrieval was verified.
- Canonical starting paths and packaged reference links were checked against
  the current wiki/source tree. The existing specialist catalog remains intact.
- Missing sources and conflicting versions must be reported explicitly;
  documentation alone establishes neither deployed release nor live health.
- Suite maintenance code/tests are unchanged by this discovery addition;
  ordinary help must remain possible without helper dependency setup. Reused
  the 19 passing helper tests from `5577887`: helper source, tests, catalog,
  helper configuration, and dependencies are unchanged. Helper runtime checks
  do not validate the new routing text; source review above covers it.
