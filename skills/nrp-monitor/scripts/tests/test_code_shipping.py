"""The generic shipping and legacy-selection contracts."""
import json

import pytest

from nrp_monitor import cluster, code_shipping, s3, state
from nrp_monitor.adapters import pv3


def test_adapter_selection(tmp_path):
    manifest = tmp_path / "job.json"
    manifest.write_text(json.dumps({
        "kind": "Job", "metadata": {},
        "spec": {"template": {"spec": {"containers": [
            {"command": ["python", "-m", "predictor_v3.utils.jobs.entry", "gate", "--spec", "s3://test/spec.json"]}
        ]}}},
    }))
    assert code_shipping.shipping_adapter({"subdir": "data prep"}) is None
    assert code_shipping.shipping_adapter({"subdir": "predictor_v3"}) is pv3
    assert code_shipping.shipping_adapter({"pkg_dir": "/somewhere/predictor_v3"}) is pv3
    assert code_shipping.shipping_adapter({"subdir": "data prep"}, manifest) is pv3
    assert code_shipping.shipping_adapter({"dirs": ["predictor_v3"]}, manifest) is None
    assert code_shipping.shipping_adapter({"adapter": "generic", "subdir": "predictor_v3"}, manifest) is None
    assert code_shipping.shipping_adapter({"adapter": "pv3", "dirs": ["data prep"]}) is pv3


def test_env_rewrite_replaces_duplicate_entries_and_value_from():
    container = {"env": [{"name": "NRP_CODE_URI", "value": "old"},
                         {"name": "NRP_CODE_URI", "valueFrom": {"secretKeyRef": {}}},
                         {"name": "OTHER", "value": "keep"},
                         {"name": "NRP_CODE_SHA256", "value": "old"}]}
    values = {"NRP_CODE_URI": "s3://test/new", "NRP_CODE_SHA256": "abcd"}
    code_shipping.rewrite_env(container, values)
    assert container["env"] == [{"name": "OTHER", "value": "keep"},
                                {"name": "NRP_CODE_URI", "value": "s3://test/new"},
                                {"name": "NRP_CODE_SHA256", "value": "abcd"}]


def test_owner_labels_keep_diagnostic_back_compat():
    assert cluster.owner_label({"labels": {"pv3/user": "old"}}) == "old"
    assert cluster.owner_label({"labels": {"pv3/user": "old", state.OWNER_LABEL_KEY: "new"}}) == "new"
    job = s3.s3_check_job_manifest("check", [])
    assert cluster.owner_label(job["metadata"]) == state.OWNER_LABEL
    assert cluster.owner_label(job["spec"]["template"]["metadata"]) == state.OWNER_LABEL
    assert "pv3/user" not in job["metadata"]["labels"]


def test_cache_location_precedence_and_reserved_prefix(monkeypatch):
    monkeypatch.setenv("NRP_MONITOR_NRP_USERNAME", "alice")
    monkeypatch.setattr(state, "OWNER", {})
    assert code_shipping.bundle_prefix({}) == "s3://braingeneerscache/nrp-monitor/code/alice"
    monkeypatch.setattr(state, "OWNER", {"code_bundle_prefix": "s3://test/owner/"})
    assert code_shipping.bundle_prefix({}) == "s3://test/owner"
    assert code_shipping.bundle_prefix({"bundle_prefix": "s3://test/task"}) == "s3://test/task"
    with pytest.raises(ValueError, match="outside braingeneerscache/braindance"):
        code_shipping.bundle_prefix({"bundle_prefix": "s3://braingeneerscache/braindance/code"})
