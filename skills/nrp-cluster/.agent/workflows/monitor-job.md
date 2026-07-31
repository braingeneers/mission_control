---
description: Monitor running Kubernetes jobs on the NRP Nautilus cluster
---

# Monitor NRP Job

// turbo-all

1. List all jobs in the braingeneers namespace:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl get jobs -n braingeneers 2>&1
```

2. List all pods (shows status: Running, Completed, Error, etc.):
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl get pods -n braingeneers 2>&1
```

3. Ask the user which pod they want to monitor (or use the most recent one).

4. Get the last 50 lines of logs from the pod:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl logs --tail=50 <pod-name> -n braingeneers 2>&1
```

5. If the user wants real-time streaming, use:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl logs -f <pod-name> -n braingeneers 2>&1
```

6. If there are errors, get detailed pod info:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl describe pod <pod-name> -n braingeneers 2>&1
```

7. Report back with:
   - Job status (Running/Completed/Failed)
   - Key log output
   - Any errors or warnings
   - Resource utilization if available

## Cleanup (when done)

8. To delete a completed or failed job:
```powershell
$env:Path = "$env:Path;$HOME\.kube\bin"; kubectl delete job <job-name> -n braingeneers 2>&1
```

## Troubleshooting

- **ImagePullBackOff**: Image not found on Docker Hub. Run `/build-push`.
- **Pending**: Not enough cluster resources. Try reducing requests.
- **OOMKilled**: Out of memory. Increase memory limits.
- **Error/CrashLoopBackOff**: Check logs for application errors.
