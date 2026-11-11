"""No real Docker daemon or notification endpoint is used by these tests."""
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import maintenance as m


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.now = 1800000000.0
        self.state = m.State(first_seen=self.now)
        self.disk = {"free_bytes": 100 * m.GIB, "total_bytes": 500 * m.GIB,
                     "free_percent": 20, "free_inode_percent": 80}
        self.prune = Mock(return_value="Total reclaimed space: 12GB")
        self.sender = Mock(return_value="delivered")
        self.writer = Mock()
        self.observer = Mock(return_value="/data/docker")
        self.measure = Mock(side_effect=lambda _: dict(self.disk))
        self.service = m.Maintenance(m.Config(), self.state, clock=lambda: self.now,
                                     disk=self.measure, daemon=self.observer,
                                     prune=self.prune, sender=self.sender, writer=self.writer)

    def tick(self, elapsed=300):
        self.service.tick()
        self.now += elapsed

    def pressure(self):
        self.disk.update(free_bytes=m.GIB, free_percent=1)

    def test_startup_daily_cleanup_and_no_success_posts(self):
        self.tick()
        self.prune.assert_called_once()
        for _ in range(3):
            self.tick()
        self.prune.assert_called_once()
        self.sender.assert_not_called()
        self.now = self.state.last_cleanup_success + m.DAY
        self.tick()
        self.assertEqual(self.prune.call_count, 2)

    def test_failed_cleanup_retries_hourly_and_alerts_when_overdue(self):
        self.prune.side_effect = subprocess.CalledProcessError(1, "docker")
        self.tick()
        self.tick()
        self.prune.assert_called_once()
        self.now = self.state.last_cleanup_attempt + m.HOUR
        self.tick()
        self.assertEqual(self.prune.call_count, 2)
        self.sender.assert_not_called()
        self.now = self.state.first_seen + 26 * m.HOUR
        self.tick()
        self.sender.assert_called_once()
        self.assertIn("26 hours", self.sender.call_args.args[1])

    def test_pressure_cleaned_up_without_alert(self):
        self.pressure()
        self.prune.side_effect = lambda: self.disk.update(free_bytes=100 * m.GIB, free_percent=20) or "reclaimed"
        self.tick()
        self.assertEqual(self.state.disk_streak, 0)
        self.sender.assert_not_called()

    def test_persistent_pressure_and_hourly_prune_limit(self):
        self.pressure()
        self.tick()
        self.sender.assert_not_called()
        self.tick()
        self.sender.assert_called_once()
        text = self.sender.call_args.args[1]
        self.assertIn("Mission Control / docker-maintenance", text)
        self.assertIn("braingeneers.gi.ucsc.edu", text)
        self.assertIn("Operator action", text)
        for _ in range(9):
            self.tick()
        self.prune.assert_called_once()
        self.sender.assert_called_once()
        self.now = self.state.last_cleanup_attempt + m.HOUR
        self.tick()
        self.assertEqual(self.prune.call_count, 2)

    def test_pressure_after_normal_daily_cleanup_triggers_early_prune(self):
        self.tick()
        self.pressure()
        self.now += m.HOUR
        self.tick()
        self.assertEqual(self.prune.call_count, 2)

    def test_daemon_failure_does_not_hide_disk_pressure(self):
        self.observer.side_effect = subprocess.TimeoutExpired("docker", 30)
        self.pressure()
        self.tick()
        self.tick()
        self.assertTrue(self.state.disk)
        self.sender.assert_called_once()
        self.tick()
        self.assertEqual(self.state.observation_failures, 3)
        self.assertTrue(any("Docker observation" in x for x in self.state.critical))

    def test_disk_observation_failure_alerts_after_three_checks(self):
        self.measure.side_effect = OSError("unavailable")
        self.tick()
        self.tick()
        self.sender.assert_not_called()
        self.tick()
        self.sender.assert_called_once()
        self.assertEqual(self.state.disk, {})

    def test_three_clear_checks_required_to_reset_suppression(self):
        self.pressure()
        self.tick()
        self.tick()
        self.disk.update(free_bytes=100 * m.GIB, free_percent=20)
        self.tick()
        self.tick()
        self.assertGreater(self.state.next_alert_attempt, self.now)
        self.tick()
        self.assertEqual(self.state.next_alert_attempt, 0)
        self.pressure()
        self.tick()
        self.tick()
        self.assertEqual(self.sender.call_count, 2)

    def test_ongoing_pressure_repeats_after_24_hours(self):
        self.pressure()
        self.tick()
        self.tick()
        self.now = self.state.next_alert_attempt - 1
        self.tick(elapsed=1)
        self.sender.assert_called_once()
        self.tick()
        self.assertEqual(self.sender.call_count, 2)

    def test_definite_delivery_failure_retries_hourly(self):
        self.sender.return_value = "failed"
        self.pressure()
        self.tick()
        self.tick()
        self.tick()
        self.sender.assert_called_once()
        self.now = self.state.next_alert_attempt
        self.tick()
        self.assertEqual(self.sender.call_count, 2)
        self.assertTrue(any("delivery" in r for r in m.health_reasons(self.state, self.now)))

    def test_ambiguous_delivery_waits_a_day(self):
        self.sender.return_value = "uncertain"
        self.pressure()
        self.tick()
        self.tick()
        self.assertEqual(self.state.next_alert_attempt, self.now - 300 + m.DAY)

    def test_cooldown_saved_before_post(self):
        self.pressure()
        self.tick()
        snapshots = []
        self.service.writer = lambda path, state: snapshots.append(asdict(state))
        def send(*_):
            self.assertEqual(snapshots[-1]["next_alert_attempt"], self.now + m.DAY)
            self.assertEqual(snapshots[-1]["notification_status"], "uncertain")
            return "delivered"
        self.service.sender = send
        self.tick()

    def test_full_state_disk_still_attempts_alert_and_cleanup(self):
        self.writer.side_effect = OSError("No space left")
        self.tick()
        self.prune.assert_called_once()
        self.sender.assert_called_once()
        self.assertIn("persist", self.sender.call_args.args[1])

    def test_restart_preserves_schedule_and_suppression(self):
        self.pressure()
        self.tick()
        self.tick()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            m.save_state(path, self.state)
            restored = m.load_state(path, self.now)
            self.assertEqual(asdict(restored), asdict(self.state))
            self.service.state = restored
            self.tick()
            self.prune.assert_called_once()
            self.sender.assert_called_once()

    def test_invalid_state_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            for content in ('{', '[]', '{"first_seen":"broken"}',
                            '{"heartbeat":NaN}', '{"disk_streak":1.5}',
                            '{"critical":[1]}', 'x' * 20000,
                            json.dumps({"heartbeat": self.now + 2 * m.DAY})):
                path.write_text(content)
                self.assertEqual(m.load_state(path, self.now).first_seen, self.now)

    def test_health_missing_stale_and_healthy(self):
        self.assertTrue(m.health_reasons(self.state, self.now))
        self.tick()
        self.assertFalse(m.health_reasons(self.state, self.now))
        self.assertTrue(m.health_reasons(self.state, self.now + 901))

    def test_low_space_and_inode_thresholds(self):
        for field, value in (("free_bytes", 9 * m.GIB), ("free_percent", 4.9),
                             ("free_inode_percent", 4.9)):
            disk = dict(self.disk)
            disk[field] = value
            self.assertTrue(m.disk_critical(disk))
        self.disk["free_inode_percent"] = None
        self.assertFalse(m.disk_critical(self.disk))

    def test_statvfs_uses_available_space_and_handles_no_inode_reporting(self):
        stats = Mock(f_blocks=100, f_frsize=4096, f_bavail=25, f_files=0)
        with patch.object(m.os, "statvfs", return_value=stats) as stat:
            disk = m.measure_disk(Path("/local"))
        stat.assert_called_once_with(Path("/local"))
        self.assertEqual(disk["free_percent"], 25)
        self.assertIsNone(disk["free_inode_percent"])

    def test_only_age_filtered_image_prune_is_used(self):
        with patch.object(m.subprocess, "run", return_value=Mock(stdout="Total reclaimed space: 0B\n")) as run:
            m.prune_images()
        self.assertEqual(run.call_args.args[0], ["docker", "--host", "unix:///var/run/docker.sock",
                         "image", "prune", "--all", "--force", "--filter", "until=336h"])
        self.assertEqual(run.call_args.kwargs["timeout"], 120)
        self.assertTrue(run.call_args.kwargs["check"])
        self.assertNotIn("DOCKER_HOST", run.call_args.kwargs["env"])

    def test_docker_timeout_is_recorded_and_loop_continues(self):
        self.prune.side_effect = subprocess.TimeoutExpired("docker", 120)
        self.tick()
        self.assertIn("TimeoutExpired", self.state.cleanup_error)
        self.assertEqual(self.state.heartbeat, self.now - 300)

    def test_daemon_must_report_a_host_root_directory(self):
        with patch.object(m, "docker", return_value=""):
            with self.assertRaises(OSError):
                m.observe_daemon()

    def test_once_respects_scheduler_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            config = m.Config(state_dir=Path(directory))
            with (config.state_dir / "maintenance.lock").open("a") as lock:
                m.fcntl.flock(lock, m.fcntl.LOCK_EX | m.fcntl.LOCK_NB)
                with patch.object(m.Config, "from_env", return_value=config), \
                     patch.object(sys, "argv", ["maintenance", "once"]):
                    self.assertEqual(m.main(), 75)

    def test_cli_once_and_read_only_status_health(self):
        with tempfile.TemporaryDirectory() as directory:
            config = m.Config(state_dir=Path(directory))
            factory = m.Maintenance
            def service(config, state):
                return factory(config, state, clock=lambda: self.now, daemon=self.observer,
                               disk=self.measure, prune=self.prune, sender=self.sender)
            with patch.object(m.Config, "from_env", return_value=config), \
                 patch.object(m, "Maintenance", side_effect=service), \
                 patch.object(sys, "argv", ["maintenance", "once"]), \
                 patch.object(m.signal, "signal"):
                self.assertEqual(m.main(), 0)
            path = config.state_dir / "state.json"
            before = path.read_bytes()
            for command in ("status", "healthcheck"):
                with patch.object(m.Config, "from_env", return_value=config), \
                     patch.object(sys, "argv", ["maintenance", command]), \
                     patch.object(m.time, "time", return_value=self.now), \
                     patch("sys.stdout", new_callable=io.StringIO):
                    self.assertEqual(m.main(), 0)
            self.assertEqual(path.read_bytes(), before)
            self.prune.assert_called_once()
            self.sender.assert_not_called()


class NotificationTests(unittest.TestCase):
    def test_success_uses_expected_channel_no_threads_no_secrets(self):
        response = Mock(status=200)
        response.read.return_value = b'{"status":"delivered","channel_id":"C08NSDULLR1","ts":"1.2"}'
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch.object(m.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(m.notify(m.Config(), "critical"), "delivered")
        request = opener.open.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"channel_id": "C08NSDULLR1", "text": "critical"})
        self.assertFalse(request.has_header("Authorization"))
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 15)

    def test_explicit_rejection_and_timeout(self):
        opener = Mock()
        for error, status in ((urllib.error.HTTPError("http://test", 503, "unavailable", {}, io.BytesIO()), "failed"),
                              (TimeoutError(), "uncertain")):
            opener.open.side_effect = error
            with patch.object(m.urllib.request, "build_opener", return_value=opener):
                self.assertEqual(m.notify(m.Config(), "critical"), status)

    def test_redirect_is_not_followed(self):
        self.assertIsNone(m.NoRedirect().redirect_request(None))

    def test_malformed_success_is_ambiguous(self):
        response = Mock(status=200)
        response.read.return_value = b'not json'
        opener = Mock()
        opener.open.return_value.__enter__ = Mock(return_value=response)
        opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch.object(m.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(m.notify(m.Config(), "critical"), "uncertain")


if __name__ == "__main__":
    unittest.main()
