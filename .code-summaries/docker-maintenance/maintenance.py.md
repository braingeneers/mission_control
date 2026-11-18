# maintenance.py

**Path:** `docker-maintenance/maintenance.py`
**Module:** `docker-maintenance.maintenance`
**Feature Area:** `docker-maintenance`
**Tier:** `full`
**Entry point:** yes — main / script execution (static candidate)

## Overview
Autonomous maintenance daemon managing Docker daemon storage: periodically prunes dangling images and builder cache, monitors disk thresholds, and issues Slack alerts on critical disk fill.

## Connections
- **Shared data:** Interacts directly with local `/var/run/docker.sock` via Docker CLI subprocesses.
- **Shared data:** Dispatches HTTP POST webhooks to Slack alerting channels.

## Dependencies
None

## Classes
### Config()
> Dataclass specifying thresholds, paths, intervals, and webhook URLs.
**Source:** `docker-maintenance/maintenance.py:26`
**Kind:** class. **Instantiated by:** unclear — see source
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `from_env(cls)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:34`
### State()
> Dataclass storing last run timestamp, last prune status, and alert rate-limiting counters.
**Source:** `docker-maintenance/maintenance.py:40`
**Kind:** class. **Instantiated by:** docker-maintenance/maintenance.py:65 (named-call hint); docker-maintenance/maintenance.py:66 (named-call hint); docker-maintenance/maintenance.py:82 (named-call hint); docker-maintenance/maintenance.py:85 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
None
### NoRedirect(urllib.request.HTTPRedirectHandler)
> unclear — see source
**Source:** `docker-maintenance/maintenance.py:139`
**Kind:** class. **Instantiated by:** docker-maintenance/maintenance.py:151 (named-call hint)
**Constructor:** inherited / implicit
**Key attributes:**
None
**Methods:**
#### `redirect_request(self, *args, **kwargs)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:140`
### Maintenance()
> unclear — see source
**Source:** `docker-maintenance/maintenance.py:168`
**Kind:** class. **Instantiated by:** docker-maintenance/maintenance.py:304 (named-call hint)
**Constructor:** `__init__(self, config, state, *, clock=time.time, daemon=observe_daemon, disk=measure_disk, prune=prune_images, sender=notify, writer=save_state)`
**Key attributes:**
None
**Methods:**
#### `persist(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** mutates instance state.
**Source:** `docker-maintenance/maintenance.py:175`
#### `tick(self)`
> unclear — see source
> **Called by:** unresolved static dispatch. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:183`

## Functions
### `load_state(path, now)`
> Reject malformed state rather than letting it disable cleanup or alerts.
> **Called by:** docker-maintenance/maintenance.py:287 (named-call hint); docker-maintenance/maintenance.py:303 (named-call hint). **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:59`
### `save_state(path, state)`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** write call (static hint).
**Source:** `docker-maintenance/maintenance.py:88`
### `docker(*args, timeout=30)`
> unclear — see source
> **Called by:** docker-maintenance/maintenance.py:109 (named-call hint); docker-maintenance/maintenance.py:117 (named-call hint). **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:98`
### `observe_daemon()`
> unclear — see source
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:108`
### `prune_images()`
> Executes `docker image prune -a` and `docker builder prune` to reclaim host disk space.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:115`
### `measure_disk(path)`
> Checks disk capacity, used bytes, and free space on Docker data root.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:122`
### `disk_critical(disk)`
> unclear — see source
> **Called by:** docker-maintenance/maintenance.py:200 (named-call hint); docker-maintenance/maintenance.py:217 (named-call hint). **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:133`
### `notify(config, text)`
> Sends formatted incident or warning messages to configured Slack webhook.
> **Called by:** unclear — see source. **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:144`
### `health_reasons(state, now)`
> unclear — see source
> **Called by:** docker-maintenance/maintenance.py:292 (named-call hint). **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:265`
### `main()`
> Daemon main loop orchestrating periodic inspection, pruning, and health reporting.
> **Called by:** docker-maintenance/maintenance.py:317 (named-call hint). **Side effects:** unclear — see source.
**Source:** `docker-maintenance/maintenance.py:280`

## Config / CLI
| Configuration / CLI and meaning |
| --- |
| `--slack-webhook URL`: Slack webhook URL for alerts (or env `SLACK_WEBHOOK_URL`). |
| `--data-root PATH`: Docker storage root directory to inspect (default: `/var/lib/docker`). |
| `--disk-threshold-gib GIB`: Minimum free disk space in GiB before triggering critical alerts (default: 50). |
| `--interval SECONDS`: Daemon loop sleep interval (default: 300 seconds). |
| `--dry-run`: Test checks without executing docker image prune commands. |

## Data Shapes
- Input: Host filesystem disk statistics (`shutil.disk_usage`) and Docker engine API socket.
- Output: State JSON saved at `/var/run/docker-maintenance.json` and JSON Slack webhook alert payloads.

## Notes
- Uses `fcntl.flock` to guarantee single-instance execution per node.
- Handles SIGTERM and SIGINT for graceful shutdown without leaving orphan prune subprocesses.
