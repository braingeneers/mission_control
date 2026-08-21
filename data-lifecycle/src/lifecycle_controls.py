"""Shared lifecycle control-object semantics.

Scientific objects are never rewritten to renew their retention.  A zero-byte
control object carries the renewal timestamp instead:

* atomic dataset: ``<dataset>/DATA_LIFECYCLE_RETENTION``
* individual file: ``<file>.DATA_LIFECYCLE_RETENTION``

The marker's S3 ``LastModified`` value is the entire retention signal.  Marker
contents and user-defined object metadata are intentionally ignored.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from lifecycle_constants import (
    FILE_RETENTION_SUFFIX,
    NOBACKUP_MARKER_NAME,
    RETENTION_MARKER_NAME,
)


def normalize_atomic_directories(paths: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    for path in paths or []:
        cleaned = str(path or "").strip()
        if cleaned.startswith("s3://"):
            cleaned = cleaned[5:]
        cleaned = cleaned.lstrip("/")
        if cleaned:
            normalized.append(cleaned)
    return normalized


def atomic_group_for_key(bucket_key: str, atomic_directories: Iterable[str] | None) -> str | None:
    key = str(bucket_key or "")
    for pattern in normalize_atomic_directories(atomic_directories):
        if pattern.endswith("/*"):
            prefix = f"{pattern[:-2].rstrip('/')}/"
            if not key.startswith(prefix):
                continue
            group_id = key[len(prefix) :].split("/", 1)[0]
            if group_id:
                return f"{prefix}{group_id}/"
            continue

        prefix = pattern.rstrip("*")
        if prefix and not prefix.endswith("/"):
            prefix = f"{prefix}/"
        if prefix and key.startswith(prefix):
            return prefix
    return None


def atomic_retention_marker(group_prefix: str) -> str:
    prefix = str(group_prefix or "").rstrip("/")
    if not prefix:
        raise ValueError("Atomic dataset prefix is required.")
    return f"{prefix}/{RETENTION_MARKER_NAME}"


def file_retention_marker(bucket_key: str) -> str:
    key = str(bucket_key or "").strip().strip("/")
    if not key:
        raise ValueError("File key is required.")
    return f"{key}{FILE_RETENTION_SUFFIX}"


def is_retention_marker(bucket_key: str) -> bool:
    key = str(bucket_key or "")
    return key.endswith(f"/{RETENTION_MARKER_NAME}") or key.endswith(FILE_RETENTION_SUFFIX)


def is_nobackup_marker(bucket_key: str) -> bool:
    return str(bucket_key or "").endswith(f"/{NOBACKUP_MARKER_NAME}")


def is_lifecycle_control_key(bucket_key: str) -> bool:
    return is_retention_marker(bucket_key) or is_nobackup_marker(bucket_key)


def lifecycle_control_mask(keys: pd.Series) -> pd.Series:
    rendered = keys.astype("string")
    return rendered.str.endswith(
        (f"/{NOBACKUP_MARKER_NAME}", f"/{RETENTION_MARKER_NAME}", FILE_RETENTION_SUFFIX),
        na=False,
    )


def retention_marker_mask(keys: pd.Series) -> pd.Series:
    rendered = keys.astype("string")
    return rendered.str.endswith((f"/{RETENTION_MARKER_NAME}", FILE_RETENTION_SUFFIX), na=False)


def retention_marker_target(
    marker_key: str,
    atomic_directories: Iterable[str] | None,
) -> tuple[str, str] | None:
    """Return ``(scope, target)`` for a valid retention marker.

    Atomic marker objects are accepted only at a configured atomic-group root.
    This prevents a coincidental filename from changing a broader dataset's
    retention timestamp.
    """

    key = str(marker_key or "")
    atomic_suffix = f"/{RETENTION_MARKER_NAME}"
    if key.endswith(atomic_suffix):
        group = key[: -len(RETENTION_MARKER_NAME)]
        if atomic_group_for_key(key, atomic_directories) == group:
            return "atomic", group
        return None
    if key.endswith(FILE_RETENTION_SUFFIX):
        target = key[: -len(FILE_RETENTION_SUFFIX)]
        if target:
            return "file", target
    return None


def scientific_inventory(inventory: pd.DataFrame) -> pd.DataFrame:
    """Return inventory rows that represent user data, not control objects."""

    return inventory.loc[~lifecycle_control_mask(inventory["BucketKey"])].copy()


def apply_effective_last_modified(
    inventory: pd.DataFrame,
    atomic_directories: Iterable[str] | None,
    *,
    authoritative_markers: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Apply file and atomic marker timestamps to scientific inventory rows.

    ``authoritative_markers`` defaults to ``inventory``.  Callers may pass the
    current Ceph inventory explicitly when evaluating another inventory so a
    stale Glacier marker can never extend retention by itself.
    """

    updated = inventory.copy()
    updated["LastModified"] = pd.to_datetime(updated["LastModified"], errors="coerce", utc=True)
    marker_source = authoritative_markers if authoritative_markers is not None else inventory
    marker_source = marker_source.copy()
    marker_source["LastModified"] = pd.to_datetime(
        marker_source["LastModified"], errors="coerce", utc=True
    )

    file_markers: dict[str, pd.Timestamp] = {}
    atomic_markers: dict[str, pd.Timestamp] = {}
    candidate_markers = marker_source.loc[
        retention_marker_mask(marker_source["BucketKey"]),
        ["BucketKey", "LastModified"],
    ]
    for row in candidate_markers.itertuples(index=False):
        if pd.isna(row.LastModified):
            continue
        target = retention_marker_target(str(row.BucketKey), atomic_directories)
        if target is None:
            continue
        scope, target_key = target
        destination = atomic_markers if scope == "atomic" else file_markers
        previous = destination.get(target_key)
        timestamp = pd.Timestamp(row.LastModified)
        if previous is None or timestamp > previous:
            destination[target_key] = timestamp

    control_mask = lifecycle_control_mask(updated["BucketKey"])
    scientific_mask = ~control_mask
    file_marker_dates = pd.to_datetime(
        updated["BucketKey"].map(file_markers), errors="coerce", utc=True
    )
    file_update_mask = scientific_mask & file_marker_dates.notna() & (
        updated["LastModified"].isna() | (file_marker_dates > updated["LastModified"])
    )
    updated.loc[file_update_mask, "LastModified"] = file_marker_dates[file_update_mask]

    keys = updated["BucketKey"].astype("string")
    for pattern in normalize_atomic_directories(atomic_directories):
        if pattern.endswith("/*"):
            prefix = f"{pattern[:-2].rstrip('/')}/"
            mask = scientific_mask & keys.str.startswith(prefix, na=False)
            if not mask.any():
                continue
            group_ids = keys.loc[mask].str[len(prefix) :].str.split("/", n=1).str[0]
            group_keys = prefix + group_ids + "/"
            group_max = updated.loc[mask].groupby(group_keys)["LastModified"].transform("max")
            marker_dates = pd.to_datetime(
                group_keys.map(atomic_markers), errors="coerce", utc=True
            )
            effective = pd.concat(
                [group_max.rename("data"), marker_dates.rename("marker")],
                axis=1,
            ).max(axis=1)
            updated.loc[mask, "LastModified"] = effective
            continue

        prefix = f"{pattern.rstrip('*').rstrip('/')}/"
        mask = scientific_mask & keys.str.startswith(prefix, na=False)
        if not mask.any():
            continue
        effective_timestamp = updated.loc[mask, "LastModified"].max()
        marker_timestamp = atomic_markers.get(prefix)
        if marker_timestamp is not None and (
            pd.isna(effective_timestamp) or marker_timestamp > effective_timestamp
        ):
            effective_timestamp = marker_timestamp
        updated.loc[mask, "LastModified"] = effective_timestamp

    updated["LastModified"] = pd.to_datetime(updated["LastModified"], errors="coerce", utc=True)
    return updated


def marker_upload_mask(
    local_inventory: pd.DataFrame,
    glacier_inventory: pd.DataFrame,
    atomic_directories: Iterable[str] | None = None,
) -> pd.Series:
    """Select local markers absent from Glacier or newer than its marker copy."""

    glacier_dates = (
        glacier_inventory[["BucketKey", "LastModified"]]
        .assign(LastModified=lambda frame: pd.to_datetime(frame["LastModified"], errors="coerce", utc=True))
        .groupby("BucketKey")["LastModified"]
        .max()
    )
    local_dates = pd.to_datetime(local_inventory["LastModified"], errors="coerce", utc=True)
    destination_dates = local_inventory["BucketKey"].map(glacier_dates)
    keys = local_inventory["BucketKey"].astype("string")
    is_marker = keys.str.endswith(FILE_RETENTION_SUFFIX, na=False)
    atomic_candidates = keys.str.endswith(f"/{RETENTION_MARKER_NAME}", na=False)
    if atomic_candidates.any():
        valid_atomic = keys.loc[atomic_candidates].map(
            lambda value: retention_marker_target(str(value), atomic_directories) is not None
        )
        is_marker.loc[atomic_candidates] = valid_atomic
    return is_marker & (destination_dates.isna() | (local_dates > destination_dates))
