---
description: Inspect Braingeneers Kubernetes Jobs on Nautilus and clean up their resources
---

# Monitor an NRP Job

Use upstream `nrp-run` → Watch without hammering the API and Collect and clean
up. For the intended Job name, set `NAME` and inspect only its pods:

```bash
kubectl --context=nautilus -n braingeneers get job "$NAME"
kubectl --context=nautilus -n braingeneers get pods -l "job-name=$NAME"
kubectl --context=nautilus -n braingeneers logs --tail=50 "$POD"
kubectl --context=nautilus -n braingeneers describe pod "$POD"
```

Set `POD` to the relevant pod listed above. Report status, log evidence, and
measured utilization. Before Job TTL removes pods and logs, persist the
evidence needed for review. Clean up owned finished/failed Jobs and any
associated ConfigMap, helper pod, or scratch PVC.

- For `ImagePullBackOff`, verify the registry, image digest, and pull access.
- For Pending, read scheduling Events and check hardware selectors before resizing.
- For `OOMKilled`, follow [smoke/profile sizing](../../SKILL.md#smokeprofile-sizing).
  On exit 137, check for ephemeral-storage eviction before increasing memory.
- For low-utilization admission denial, follow the
  [namespace-wide check](../../SKILL.md#resource-sizing-and-utilization).
