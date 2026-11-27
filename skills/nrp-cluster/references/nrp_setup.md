# Braingeneers NRP setup

Use the upstream `nrp` skill's Access, Usage policies, GPUs, and Storage
sections for cluster setup, OIDC troubleshooting, GPU selection, and Ceph
configuration. See the [fallback digest](nrp_rules_digest.md) if unavailable.

Use context `nautilus`, namespace `braingeneers`, and Job names matching
`<user>-<purpose>`, where `<user>` is your NRP username (for example,
`alex-sortbench`).

## S3 storage

| Setting | Value |
|---|---|
| Bucket | `braingeneersdev` |
| Prefix | Use the authorized workstream prefix |
| In-cluster endpoint | `http://rook-ceph-rgw-nautiluss3.rook` |
| External west endpoint | `https://s3-west.nrp-nautilus.io` |

Read inputs and write outputs from inside the cluster. The pipeline template's
`s3_utils.py` provides adaptive retries with jitter and paginates listings.
For other regions and transfer tooling see upstream `nrp` → Storage.

## Credential Storage

For local S3 access, use an approved AWS profile or ephemeral
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment values. Use
`WANDB_API_KEY` locally only when needed. Keep local credentials out of version
control and command output.

In a Job, use `secretKeyRef` to the existing lab Secret and expected key for
each required credential. If the workload expects AWS environment variables,
confirm the operator-managed Secret name and keys before wiring them. In
deployed lab S3 readers that already use the `prp-s3-credentials` file mount,
preserve that contract when diagnosing existing workloads. Never copy the
credential file or use `envsubst` to render credential values into a manifest.

## Weights & Biases (W&B)

Add `wandb` to the image dependencies when needed. Set `WANDB_PROJECT` for the
pipeline and expose `WANDB_API_KEY` from `wandb-credentials/api-key` via
`secretKeyRef`. The client authenticates using that environment variable:

```python
import wandb

wandb.init(project="your-project-name")
```

See [hosted LLMs](hosted-llms.md) or [Brave Search](brave-search.md) for those
existing lab Secrets and task-scoped injection.

## ConfigMaps, Secrets and etcd

Follow upstream `nrp` → Hard rules for file payloads and size checks. The lab
also requires cleanup verification for Job-scoped settings. Reuse shared
settings when their lifecycle is shared. Keep run-specific settings isolated
when concurrent Jobs need different values, with a Job owner reference and TTL
or explicit cleanup covering completion, cancellation, and launch failure.

Use an image for large or reusable code. For a registered monitor task,
`NRP_TASK=<task> nrp-task ship NAME [--from SUBDIR]` pushes the Git task branch,
publishes the bundle to `braingeneerscache`, the expiring S3 bucket used by
Workflows, and prints `NRP_CODE_URI`,
`NRP_CODE_SHA256`, and startup lines to download, verify, extract, and run it.
Authenticated lab users are trusted. The bucket is appropriate for bundles
from private repos as well. See [Shipping code](../../nrp-monitor/references/tasks.md#shipping-code).
This replaces `nrp-task configmap`. If NRP disallows the S3 tarball, use the image.

Measure the namespace ConfigMap total (read-only):

```bash
kubectl --context=nautilus -n braingeneers get cm -o json --chunk-size=50 |
  jq '[.items[] | tojson | length] | {count: length, MB: ((add // 0) / 1e6)}'
```

Check consumers and recoverability before deleting ConfigMaps you own or have
authorization to clean up. An empty pod reference list alone does not prove
that a map is unused.
