# Find lab guidance

Use this for service discovery, how-tos, access questions, onboarding, and lab
topics outside the specialist catalog. Retrieve the sources relevant to the
question; this reference is a starting map, not a copy of the lab's procedures.

## Find and read the source

1. Use an available Braingeneers wiki checkout when relevant. Find it in the
   workspace or known checkouts; do not assume the user's machine has a sibling
   `../wiki` or scan their whole home directory. Read `README.md` for task routes
   and the **Service Directory**, then the relevant guide or index.
2. Search filenames with `rg --files` and content with `rg -n -i` using the
   user's terms, service/device names, and synonyms. For an unfamiliar topic,
   search beyond the indexes, including device, ephys, imaging, and shared guides.
   Read matching sections and follow their source links; filenames or snippets
   alone are not enough to explain a procedure.
3. Without a local checkout, retrieve the
   [wiki home](https://github.com/braingeneers/wiki/blob/main/README.md) using
   available browsing or GitHub tools. Some lab documentation is in private
   GitHub repositories: use an existing authorized session or checkout. If
   access fails, explain the GitHub organization-access/sign-in requirement and
   the helpdesk route below; do not ask for a lab API token or raw GitHub token.
   A GitHub 404 can mean missing permissions, not a missing procedure. Reading
   an accessible public page needs neither lab credentials nor GitHub sign-in.
   Resolve relative links against that page's repository directory. If browsing
   is unavailable but GitHub CLI is available, these read-only requests retrieve
   a page or list candidate paths:

   ```bash
   gh api -H 'Accept: application/vnd.github.raw+json' 'repos/braingeneers/wiki/contents/README.md?ref=main'
   gh api 'repos/braingeneers/wiki/git/trees/main?recursive=1' --jq '.tree[] | select(.type == "blob") | .path'
   ```

   Replace `README.md` with the relevant path to read a guide. Search GitHub code
   when available; if full-text search is needed and remote search is inadequate,
   a temporary shallow wiki checkout is an option. Do not require a clone or
   GitHub sign-in just to read an accessible public page. If an API tree response
   is truncated, list the relevant subdirectory instead of concluding it is absent.
4. Follow current indexes and the owning service/library's maintained docs.
   [Documentation ownership](https://github.com/braingeneers/wiki/blob/main/shared/documentation-maintenance.md#authoritative-locations)
   identifies canonical guides. Treat archived pages and superseded instructions
   as history. When local freshness is uncertain or a procedure depends on a
   current version, check upstream `main` or the relevant maintained source.
   Do not overwrite or pull a user's modified checkout to refresh your reading.
5. Cite the exact guide, section, or repository page used. State uncertainty if
   sources conflict or cannot be retrieved. Documentation describes intended
   behavior; it is not proof that a service is currently healthy or running a
   particular release. Check live state only when the user's task needs it, with
   the applicable specialist and access rules.

## Starting points

Paths below are relative to `braingeneers/wiki` on `main`; follow updated links
from its indexes if pages move. Resolve service URLs through the Service
Directory rather than maintaining a second list of deployed hostnames here.

| Question | Start with |
| --- | --- |
| Which service should I use? Where is the viewer or console? | `README.md` → Service Directory → service and **Docs** links |
| How do I upload a recording, images, or a sequencing delivery? | `api_data/index.md` → dataset layout/naming → linked Uploader user instructions; follow the sequencing route when applicable |
| How do I find or download data in a browser? | `api_data/index.md` → `api_data/data-explorer.md` |
| How do I read data in Python or transfer files with S3? | Data index → linked Python tools; `api_data/s3-quickstart.md` and `api_data/s3-reference.md` for transfers and endpoints |
| How do I get access or join the lab? | `shared/onboarding.md` and `shared/permissions.md`; distinguish web-service, S3, and cluster credentials |
| How do I run code or read data on NRP? | `shared/nrp/index.md` → first-job, storage, or S3-from-jobs guide |
| How do metadata, NWB/DANDI publication, or backup/retention work? | Data index → the corresponding metadata, publication, or retention guide |
| How do I use a device or follow an experimental procedure? | Wiki home → IoT Devices or scientific guides; search the whole wiki and linked owning repositories for the named device/procedure |

## Answer and hand off

Lead with the service or next useful step. Give a short explanation in ordinary
language, a source link, and only the prerequisites and steps relevant to this
user. Expand if they need a walkthrough. For a broad access question, offer the
browser route and explain when Python/S3 or cluster access becomes useful;
ask which route they need only when that choice affects the next steps.

Use a specialist when executing its operations, inspecting actual datasets or
protected service state, or giving technical guidance that requires its
contracts. Preserve the distinction between explaining an upload, uploading to
lab storage, editing metadata, and publishing externally. If no specialist
covers a requested action, follow its owning documented procedure and existing
authorization boundaries; stop for a missing prerequisite or unclear effect.
Never invent an API or use a metadata/publication endpoint as a file-upload substitute.

If a procedure cannot be found after checking accessible indexes, searching the wiki, and
following plausible owning links, say what was checked and what remains unknown.
Ask for a device/model, experiment type, or other missing context when useful.
For lab help, link
[permissions and support](https://github.com/braingeneers/wiki/blob/main/shared/permissions.md#where-to-get-help),
which currently names `#braingeneers-helpdesk` on UCSC GI Slack. Provide the route;
do not send a message without a request. Do not infer an undocumented wet-lab
protocol, operating parameter, access entitlement, or device command from general knowledge.
