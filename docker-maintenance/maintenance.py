#!/usr/bin/env python3
"""Bounded Docker image maintenance and critical storage alerts."""
import argparse
from dataclasses import asdict, dataclass, field
import fcntl
import json
import logging
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request

LOG = logging.getLogger("docker-maintenance")
HOUR = 3600
DAY = 24 * HOUR
INTERVAL = 300
GIB = 1024 ** 3


@dataclass(frozen=True)
class Config:
    state_dir: Path = Path("/local/docker-maintenance")
    disk_path: Path = Path("/local")
    server: str = "braingeneers.gi.ucsc.edu"
    channel: str = "C08NSDULLR1"
    notification_url: str = "http://notification-service:8000/v1/slack"

    @classmethod
    def from_env(cls):
        return cls(server=os.environ.get("MAINTENANCE_SERVER", cls.server),
                   channel=os.environ.get("MAINTENANCE_SLACK_CHANNEL_ID", cls.channel))


@dataclass
class State:
    first_seen: float = 0.0
    heartbeat: float = 0.0
    last_cleanup_attempt: float = 0.0
    last_cleanup_success: float = 0.0
    next_alert_attempt: float = 0.0
    observation_failures: int = 0
    disk_streak: int = 0
    recovery_streak: int = 0
    cleanup_error: str = ""
    observation_error: str = ""
    state_error: str = ""
    cleanup_result: str = "not yet attempted"
    notification_status: str = "not needed"
    docker_root: str = ""
    disk: dict = field(default_factory=dict)
    critical: list = field(default_factory=list)


def load_state(path, now):
    """Reject malformed state rather than letting it disable cleanup or alerts."""
    try:
        if path.stat().st_size > 16384:
            raise ValueError("oversized state")
        data = json.loads(path.read_text())
        state = State(**data)
        defaults = State()
        for name, value in asdict(state).items():
            default = getattr(defaults, name)
            if isinstance(default, (int, float)):
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("invalid counter/timestamp")
                if isinstance(default, int) and type(value) is not int:
                    raise ValueError("nonintegral counter")
                if isinstance(default, float) and value > now + DAY:
                    raise ValueError("future timestamp")
            elif type(value) is not type(default):
                raise ValueError("invalid state field")
        if not all(isinstance(item, str) for item in state.critical):
            raise ValueError("invalid critical conditions")
        return state
    except FileNotFoundError:
        return State(first_seen=now)
    except (OSError, ValueError, TypeError):
        LOG.warning("State missing/unreadable/invalid; rebuilding observation and schedule")
        return State(first_seen=now)


def save_state(path, state):
    # One bounded file, replaced atomically; no accumulating history or outbox.
    temporary = path.with_name(".state.json.tmp")
    with temporary.open("w") as stream:
        json.dump(asdict(state), stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def docker(*args, timeout=30):
    result = subprocess.run(
        ["docker", "--host", "unix:///var/run/docker.sock", *args],
        env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
             "DOCKER_CONFIG": "/tmp/docker-maintenance-config"},
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    return result.stdout.strip()


def observe_daemon():
    root = docker("info", "--format", "{{.DockerRootDir}}")
    if not root.startswith("/"):
        raise OSError("Docker did not report a root directory")
    return root


def prune_images():
    # Docker protects images associated with ANY container, including stopped ones.
    output = docker("image", "prune", "--all", "--force", "--filter", "until=336h",
                    timeout=120)
    return output.splitlines()[-1][:500] if output else "completed (no output)"


def measure_disk(path):
    stats = os.statvfs(path)
    total = stats.f_blocks * stats.f_frsize
    if total <= 0:
        raise ValueError("filesystem reports no capacity")
    return {"free_bytes": stats.f_bavail * stats.f_frsize, "total_bytes": total,
            "free_percent": 100 * stats.f_bavail / stats.f_blocks,
            "free_inode_percent": (100 * stats.f_favail / stats.f_files
                                   if stats.f_files else None)}


def disk_critical(disk):
    return (disk["free_bytes"] < 10 * GIB or disk["free_percent"] < 5
            or (disk["free_inode_percent"] is not None
                and disk["free_inode_percent"] < 5))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def notify(config, text):
    request = urllib.request.Request(
        config.notification_url,
        data=json.dumps({"channel_id": config.channel, "text": text}).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
            result = json.loads(response.read(8192))
            if (response.status == 200 and result.get("status") == "delivered"
                    and result.get("channel_id") == config.channel and result.get("ts")):
                return "delivered"
    except urllib.error.HTTPError as error:
        # An explicit HTTP rejection can be retried. Do not log message bodies.
        LOG.warning("Notification rejected: HTTP %s", error.code)
        error.close()
        return "failed"
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    # A timeout or malformed success response may have followed actual delivery.
    LOG.warning("Notification delivery uncertain; suppressing retries for 24 hours")
    return "uncertain"


class Maintenance:
    def __init__(self, config, state, *, clock=time.time, daemon=observe_daemon,
                 disk=measure_disk, prune=prune_images, sender=notify, writer=save_state):
        self.config, self.state = config, state
        self.clock, self.daemon, self.disk = clock, daemon, disk
        self.prune, self.sender, self.writer = prune, sender, writer

    def persist(self):
        try:
            self.state.state_error = ""
            self.writer(self.config.state_dir / "state.json", self.state)
        except OSError as error:
            self.state.state_error = f"Cannot persist maintenance state ({type(error).__name__})"
            LOG.error(self.state.state_error)

    def tick(self):
        state, now = self.state, self.clock()
        state.heartbeat = now
        # Disk observation remains independent of Docker daemon availability.
        observation_errors = []
        try:
            state.disk = self.disk(self.config.disk_path)
        except (OSError, ValueError) as error:
            state.disk = {}
            observation_errors.append(f"disk observation failed ({type(error).__name__})")
        try:
            state.docker_root = self.daemon()
        except (OSError, subprocess.SubprocessError) as error:
            observation_errors.append(f"Docker observation failed ({type(error).__name__})")
        state.observation_error = "; ".join(observation_errors)
        state.observation_failures = state.observation_failures + 1 if observation_errors else 0

        pressure = bool(state.disk) and disk_critical(state.disk)
        scheduled = not state.last_cleanup_success or now - state.last_cleanup_success >= DAY
        retry_ready = not state.last_cleanup_attempt or now - state.last_cleanup_attempt >= HOUR
        if (scheduled or pressure) and retry_ready:
            state.last_cleanup_attempt = now
            self.persist()  # Preserve hourly rate limit even if killed during pruning.
            try:
                state.cleanup_result = self.prune()
                state.last_cleanup_success = self.clock()
                state.cleanup_error = ""
                LOG.info("Image cleanup: %s", state.cleanup_result)
            except (OSError, subprocess.SubprocessError) as error:
                state.cleanup_error = f"Image cleanup failed ({type(error).__name__})"
                state.cleanup_result = state.cleanup_error
                LOG.warning(state.cleanup_error)
            try:
                state.disk = self.disk(self.config.disk_path)
                pressure = disk_critical(state.disk)
            except (OSError, ValueError):
                state.disk = {}
                state.observation_error = "disk observation failed after cleanup"
                state.observation_failures = max(1, state.observation_failures)
                pressure = False

        state.disk_streak = state.disk_streak + 1 if pressure else 0
        reasons = []
        if state.disk_streak >= 2:
            reasons.append("Critical disk capacity remains after age-limited cleanup")
        if state.observation_failures >= 3:
            reasons.append(state.observation_error)
        if now - (state.last_cleanup_success or state.first_seen) >= 26 * HOUR:
            reasons.append("No successful image cleanup for 26 hours")
        self.persist()
        if state.state_error:
            reasons.append(state.state_error)
        state.critical = reasons
        # Transient observation errors/pressure do not count as recovery.
        clear = (not reasons and not pressure and not state.observation_error
                 and not state.cleanup_error)
        state.recovery_streak = min(3, state.recovery_streak + 1) if clear else 0
        if state.recovery_streak >= 3:
            state.next_alert_attempt = 0
            state.notification_status = "not needed"
        if reasons and now >= state.next_alert_attempt:
            # Save cooldown BEFORE sending, covering process death after delivery.
            state.next_alert_attempt = now + DAY
            state.notification_status = "uncertain"
            self.persist()
            text = (f"[Mission Control / docker-maintenance] {self.config.server}: "
                    + "; ".join(reasons) + ". ")
            if state.disk:
                inodes = state.disk["free_inode_percent"]
                inode_text = f"{inodes:.1f}%" if inodes is not None else "not reported"
                text += (f"Free: {state.disk['free_bytes'] / GIB:.1f} GiB "
                         f"({state.disk['free_percent']:.1f}%). "
                         f"Free inodes: {inode_text}. ")
            text += (f"Last cleanup: {state.cleanup_result}. "
                     "Operator action: inspect server storage and docker-maintenance logs; "
                     "restore free space or repair maintenance/daemon access.")
            state.notification_status = self.sender(self.config, text)
            if state.notification_status == "failed":
                state.next_alert_attempt = now + HOUR
        self.persist()


def health_reasons(state, now):
    reasons = list(state.critical)
    if not state.heartbeat or now - state.heartbeat > 900:
        reasons.append("Maintenance heartbeat missing or older than 15 minutes")
    if state.observation_failures:
        reasons.append(state.observation_error)
    if now - (state.last_cleanup_success or state.first_seen) >= 26 * HOUR:
        reasons.append("Successful cleanup is overdue")
    if state.state_error:
        reasons.append(state.state_error)
    if state.notification_status in ("failed", "uncertain"):
        reasons.append("Critical alert delivery failed or is uncertain")
    return reasons


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s docker-maintenance %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "once", "status", "healthcheck"), default="run", nargs="?")
    args = parser.parse_args()
    config = Config.from_env()
    path = config.state_dir / "state.json"
    state = load_state(path, time.time())
    if args.command == "status":
        print(json.dumps(asdict(state), indent=2))
        return 0
    if args.command == "healthcheck":
        reasons = health_reasons(state, time.time())
        print("; ".join(reasons) if reasons else "Maintenance healthy")
        return int(bool(reasons))
    config.state_dir.mkdir(parents=True, exist_ok=True)
    with (config.state_dir / "maintenance.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            LOG.error("Another maintenance process holds the lock")
            return 75
        # Load inside the lock so a competing once/run cannot act on stale state.
        state = load_state(path, time.time())
        service = Maintenance(config, state)
        stop = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.set())
        while not stop.is_set():
            service.tick()
            if args.command == "once":
                break
            stop.wait(INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
