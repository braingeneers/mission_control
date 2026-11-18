# lifecycle_constants.py

**Path:** `data-lifecycle/src/lifecycle_constants.py`
**Module:** `data-lifecycle.src.lifecycle_constants`
**Feature Area:** `data-lifecycle`
**Tier:** `full`
**Entry point:** no — library or imported component

## Overview
Defines reserved constant object names and marker suffixes for the Braingeneers data lifecycle retention management subsystem.

## Connections
- **Used by:** `data-lifecycle.src.lifecycle_controls` — import consumer hint; not a proven runtime call.
- **Shared data:** Imported by `lifecycle_controls.py`.

## Dependencies
None

## Classes
None

## Functions
None

## Config / CLI
None

## Data Shapes
- `RETENTION_MARKER_NAME = 'DATA_LIFECYCLE_RETENTION'`
- `FILE_RETENTION_SUFFIX = '.DATA_LIFECYCLE_RETENTION'`
- `NOBACKUP_MARKER_NAME = 'NOBACKUP'`

## Notes
- Zero-byte S3 control objects with these names carry renewal timestamps in their S3 `LastModified` metadata.
- Prevents re-uploading large scientific files solely to update retention timestamps.
