"""Validate and normalize one annotation batch: python validate_batch.py BATCH.json OUT.json

Exit 0 when every file in the batch has an overview; checks manifest hashes and rewrites OUT.json
(the helper re-verifies them against disk at build time) and list-typed full-tier fields.
Works for output from any annotator.
"""
import json
import sys

batch, out = json.load(open(sys.argv[1])), sys.argv[2]
try:
    data = json.load(open(out))
except Exception as exc:
    sys.exit(f"bad/missing json: {exc}")
if not isinstance(data, dict):
    sys.exit("annotation must be an object")
want = {f["path"]: f["sha256"] for f in batch["files"]}
missing = [p for p in want if not isinstance(data.get(p), dict) or not isinstance(data[p].get("overview"), str) or not data[p].get("overview", "").strip()]
if missing:
    sys.exit(f"missing {len(missing)}/{len(want)}: {missing[:3]}")
for path, sha in want.items():
    if data[path].get("source_sha256") != sha:
        sys.exit(f"hash mismatch: {path}")
    if batch["tier"] == "full":
        for key in ("config", "data_shapes", "notes", "connections"):
            value = data[path].get(key, [])
            data[path][key] = value if isinstance(value, list) else [str(value)]
json.dump({p: data[p] for p in want}, open(out, "w"), indent=1)
print("valid", len(want))
