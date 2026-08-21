import csv
import re

RCLONE_DOT_SEGMENT = '．'
RCLONE_DOT_DOT_SEGMENT = '．．'
EMBEDDED_S3_SCHEME_RE = re.compile(r's3:/(?!/)')
EMBEDDED_S3_SCHEME_CANONICAL_RE = re.compile(r's3://')


def normalize_put_key(raw_key):
    if raw_key is None:
        return None

    key = str(raw_key).strip()
    if not key:
        return None

    # Some generated puts entries have carried embedded carriage returns
    # (or their visible symbol U+240D). These should not be part of S3 keys.
    key = key.replace('\r', '').replace('\u240d', '')

    if key.startswith('s3://'):
        key = key[len('s3://'):]
    key = key.lstrip('/')

    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        key = key[1:-1].strip()
        if key.startswith('s3://'):
            key = key[len('s3://'):]
        key = key.lstrip('/')

    return normalize_bucket_object_key(key)


def normalize_bucket_object_key(raw_key):
    if raw_key is None:
        return None

    key = str(raw_key).strip()
    if not key or '/' not in key:
        return None

    bucket, object_key = key.split('/', 1)
    if not bucket or not object_key:
        return None

    normalized_object_key = normalize_object_key(object_key)
    if not normalized_object_key:
        return None
    return f'{bucket}/{normalized_object_key}'


def normalize_object_key(object_key):
    if object_key is None:
        return None

    normalized = str(object_key).replace('\r', '').replace('\u240d', '')
    normalized = normalize_rclone_dot_segments(normalized)
    normalized = restore_embedded_s3_scheme(normalized)
    return normalized


def load_put_keys(puts_file):
    keys = []
    malformed = []

    with open(puts_file, 'r', encoding='utf8', newline='') as file_handle:
        reader = csv.reader(file_handle)
        for line_no, row in enumerate(reader, 1):
            if not row:
                continue
            raw_key = ','.join(row).strip()
            normalized_key = normalize_put_key(raw_key)
            if normalized_key is None:
                malformed.append((line_no, raw_key))
                continue
            keys.append(normalized_key)

    if malformed:
        sample_lines = '\n'.join(f'  line {line_no}: {raw_key!r}' for line_no, raw_key in malformed[:10])
        more_label = '\n  ...' if len(malformed) > 10 else ''
        raise ValueError(
            (
                f'Found {len(malformed)} malformed PUT key(s) in {puts_file}. '
                'Failing fast before upload. '
                "Expected keys in 'bucket/object' form.\n"
                f'{sample_lines}{more_label}'
            )
        )

    return keys


def normalize_rclone_dot_segments(object_key):
    segments = object_key.split('/')
    normalized_segments = []
    for segment in segments:
        if segment == RCLONE_DOT_SEGMENT:
            normalized_segments.append('.')
        elif segment == RCLONE_DOT_DOT_SEGMENT:
            normalized_segments.append('..')
        else:
            normalized_segments.append(segment)
    return '/'.join(normalized_segments)


def denormalize_rclone_dot_segments(object_key):
    segments = object_key.split('/')
    normalized_segments = []
    for segment in segments:
        if segment == '.':
            normalized_segments.append(RCLONE_DOT_SEGMENT)
        elif segment == '..':
            normalized_segments.append(RCLONE_DOT_DOT_SEGMENT)
        else:
            normalized_segments.append(segment)
    return '/'.join(normalized_segments)


def restore_embedded_s3_scheme(object_key):
    return EMBEDDED_S3_SCHEME_RE.sub('s3://', object_key)


def collapse_embedded_s3_scheme(object_key):
    return EMBEDDED_S3_SCHEME_CANONICAL_RE.sub('s3:/', object_key)


def build_source_lookup_candidates(source_key):
    normalized_key = normalize_bucket_object_key(source_key)
    if normalized_key is None:
        return []

    bucket, object_key = normalized_key.split('/', 1)
    object_variants = [
        object_key,
        denormalize_rclone_dot_segments(object_key),
        collapse_embedded_s3_scheme(object_key),
        collapse_embedded_s3_scheme(denormalize_rclone_dot_segments(object_key)),
    ]

    candidates = []
    seen = set()
    for variant in object_variants:
        candidate = f'{bucket}/{variant}'
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates
