# NRP rules fallback — 2026-11-25

Fallback for agents without NRP's `nrp-nautilus` plugin. Based on
[plugin commit 98bc617](https://github.com/nrp-nautilus/sdsc-marketplace/tree/98bc617/plugins/nrp-nautilus)
(0.3.0). The current plugin and [NRP llms.txt](https://nrp.ai/llms.txt) take
precedence over this digest. Use the stricter instruction if they differ and
apply the [Braingeneers lab rules](../SKILL.md#stricter-lab-rules) as well.

- Accept the AUP. NRP is for nonprofit, noncommercial use. Keep protected data off NRP and archive elsewhere. For access, use `kubectl`, `kubelogin`, and the NRP kubeconfig from [NRP access](https://nrp.ai/config).
- Use Jobs with terminating commands for compute. No indefinite sleep or log tail in a Job. Bare interactive pods expire after six hours and are capped at 2 GPUs, 16 CPUs, and 32 GB RAM. Idle services use a low-request CPU Deployment, normally purged after two weeks. Finished Jobs and logs normally expire after one day.
- Declare CPU, memory, and ephemeral-storage requests and limits on every container. Keep limits within 20% of requests for Jobs and pods, and match them above about 100 pods or Jobs. Size from measurements. Keep GPU use above 40%, CPU at 20–200%, and memory RSS at 20–150% of requests. At most four pods may be outside these bands per user. Pods requesting at most 1 CPU and 2 GB memory are exempt.
- Submit at most 400 Jobs at once and stay within namespace pod quota. Batch short tasks into capped Indexed Jobs. Avoid loops that create one Job per item and frequent CronJob scheduling.
- Use ConfigMaps for a few KB of settings and Secrets for credentials. Keep files and inline payloads out of the API objects. Avoid splitting or encoding payloads or changing the apply verb to pass checks. Preflight warns above 113 KiB and blocks above 256 KiB. Give each Job-owned object an owner reference or clean it up with the Job.
- Use keyed tolerations only for authorized taints. Never tolerate system or issue taints, set `nodeName` or `CUDA_VISIBLE_DEVICES`, or force-delete resources. Leave priority unset for ordinary work and verify any special class in current NRP policy. Check NRP's [GPU guidance](https://nrp.ai/documentation/userdocs/running/gpu-pods/) before choosing a GPU, especially reservation-only A100s. Avoid DaemonSets, NodePort/LoadBalancer Services, and GPUs in Deployments.
- Verify context and namespace. Run upstream preflight on the rendered file when available, then run server-side dry-run. Fix blocks, denials, and warnings, show the manifest and resource summary, and apply after approval. Diagnose denials without bypassing checks. Escalate stuck terminating resources to [NRP Support](https://nrp.ai/contact/).
- Transfer bulk files through S3, including results. The plugin's `kubectl cp` guidance applies only to PVCs. The lab moves data through S3 and does not normally use PVCs. Use the upstream [storage reference](https://github.com/nrp-nautilus/sdsc-marketplace/blob/98bc617/plugins/nrp-nautilus/skills/nrp/references/storage.md) for regional endpoints and PVCs, and the [managed LLM documentation](https://nrp.ai/llms/) for live models, request settings, limits, and access.
