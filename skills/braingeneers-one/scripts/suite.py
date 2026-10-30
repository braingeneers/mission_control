#!/usr/bin/env python3
"""Maintain only cataloged Braingeneers skills; never run lab operations."""

import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

try:
    import yaml
except ImportError:
    sys.exit("The helper needs PyYAML in this Python environment. See references/maintenance.md.")


ONE = Path(__file__).resolve().parents[1]
TRACKING = {"github-repo", "github-ref", "github-tree-sha", "github-path", "github-pinned"}


class Failure(Exception):
    pass


def command(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Failure("GitHub CLI unavailable or timed out; check installation/network and retry.") from exc
    if result.returncode:
        # Do not echo subprocess output: authentication diagnostics can contain credentials.
        raise Failure("GitHub CLI request failed; check repository access, gh auth status, and network.")
    return result.stdout


def api(endpoint):
    try:
        return json.loads(command(["gh", "api", endpoint]))
    except ValueError as exc:
        raise Failure("GitHub returned an unexpected response.") from exc


def frontmatter(data):
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)\Z", data.decode(), re.S)
    if not match:
        raise Failure("Missing SKILL.md YAML frontmatter.")
    header = yaml.safe_load(match[1])
    if not isinstance(header, dict) or not isinstance(header.get("metadata", {}), dict):
        raise Failure("Unsupported SKILL.md metadata.")
    return header, match[2].lstrip("\r\n")


def without_tracking(header):
    result = copy.deepcopy(header)
    meta = result.get("metadata", {})
    for key in TRACKING:
        meta.pop(key, None)
    if not meta:
        result.pop("metadata", None)
    return result


def files_at(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise Failure("Symlink or non-directory installation; preserve and maintain through its owner.")
    files = {}
    for item in directory.rglob("*"):
        if item.is_symlink():
            raise Failure("Contains a symlink; preserve and maintain through its owner.")
        if item.is_dir():
            continue
        if not item.is_file():
            raise Failure("Contains an unsupported filesystem object.")
        files[item.relative_to(directory).as_posix()] = item.read_bytes()
    return files


def fingerprint(directory):
    return {name: hashlib.sha256(data).hexdigest() for name, data in files_at(directory).items()}


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_catalog(path=ONE / "references/catalog.json"):
    catalog = json.loads(path.read_text())
    if catalog.get("schema_version") != 1:
        raise Failure("Unsupported catalog version.")
    skills = {}
    for item in catalog["skills"]:
        if (not re.fullmatch(r"[a-z0-9-]+", item["name"])
                or not re.fullmatch(r"braingeneers/[A-Za-z0-9_-]+", item["repo"])
                or item["branch"] != "main"
                or Path(item["path"]).name != item["name"]
                or any(part in ("..", ".") for part in item["path"].split("/"))
                or item["path"].startswith("/") or item["name"] in skills):
            raise Failure("Invalid or duplicate catalog entry.")
        skills[item["name"]] = item
    return skills


class Suite:
    def __init__(self, root, state_dir, catalog=None):
        self.root = Path(root).absolute()
        self.state_dir = Path(state_dir).absolute()
        self.catalog = load_catalog() if catalog is None else catalog
        self.state_file = self.state_dir / "state.json"
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        if self.state.get("root", str(self.root)) != str(self.root):
            raise Failure("State belongs to a different skills directory; choose a separate --state-dir.")
        self.state["root"] = str(self.root)
        self.state.setdefault("managed", {})
        self.trees = {}

    def save(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2) + "\n")
        os.replace(temporary, self.state_file)

    def metadata(self, item, directory):
        header, _ = frontmatter((directory / "SKILL.md").read_bytes())
        meta = header.get("metadata", {})
        if meta.get("github-pinned"):
            raise Failure("Explicitly pinned; left unchanged.")
        repo = str(meta.get("github-repo", "")).rstrip("/")
        if repo.endswith(".git"):
            repo = repo[:-4]
        if (header.get("name") != item["name"]
                or repo != "https://github.com/" + item["repo"]
                or meta.get("github-path") != item["path"]
                or not re.fullmatch(r"[0-9a-f]{40}", str(meta.get("github-tree-sha", "")))):
            raise Failure("Unknown source or path; left unchanged.")
        return meta

    def verify(self, item, directory, tree_sha):
        """Check every file against immutable source; ignore only gh's injected tracking fields."""
        key = (item["repo"], tree_sha)
        if key not in self.trees:
            self.trees[key] = api(f"repos/{item['repo']}/git/trees/{tree_sha}?recursive=1")
        tree = self.trees[key]
        if tree.get("truncated"):
            raise Failure("Source tree was truncated; cannot verify installation.")
        expected = {entry["path"]: entry for entry in tree["tree"] if entry["type"] != "tree"}
        local = files_at(directory)
        if local.keys() != expected.keys():
            raise Failure("Local files added or missing; left unchanged.")
        for name, entry in expected.items():
            if entry["type"] != "blob" or entry["mode"] not in ("100644", "100755"):
                raise Failure("Unsupported upstream object; left unchanged.")
            if Path(name).name == "SKILL.md":
                upstream = api(f"repos/{item['repo']}/git/blobs/{entry['sha']}")
                original_header, original_body = frontmatter(base64.b64decode(upstream["content"]))
                local_header, local_body = frontmatter(local[name])
                if without_tracking(local_header) != without_tracking(original_header) or local_body != original_body:
                    raise Failure("Local instructions modified; left unchanged.")
            elif blob_sha(local[name]) != entry["sha"]:
                raise Failure("Local files modified; left unchanged.")

    def enroll(self, item):
        directory = self.root / item["name"]
        current = fingerprint(directory)
        meta = self.metadata(item, directory)
        recorded = self.state["managed"].get(item["name"])
        if recorded:
            if recorded["files"] != current or recorded["tree"] != meta["github-tree-sha"]:
                raise Failure("Changed since last managed installation; left unchanged.")
        else:
            self.verify(item, directory, meta["github-tree-sha"])
            self.state["managed"][item["name"]] = {"files": current, "tree": meta["github-tree-sha"]}
        return meta["github-tree-sha"]

    def latest(self, item):
        # Resolve branch once, then address every subsequent request by immutable commit.
        commit = api(f"repos/{item['repo']}/commits/{quote(item['branch'], safe='')}")["sha"]
        parent, _, name = item["path"].rpartition("/")
        listing = api(f"repos/{item['repo']}/contents/{parent}?ref={commit}")
        match = next((entry for entry in listing if entry["name"] == name and entry["type"] == "dir"), None)
        if not match:
            raise Failure("Skill directory missing upstream; left unchanged.")
        return commit, match["sha"]

    def status(self, daily=False):
        now = time.time()
        cache = self.state.get("check", {})
        interval = 86400 if cache.get("complete") else 3600
        if daily and 0 <= now - cache.get("time", 0) < interval:
            # Never present a cached freshness result for subsequently edited files.
            if cache.get("files") == self.installed_fingerprints():
                return {"cached": True, **cache}
        rows, complete = [], True
        for name, item in self.catalog.items():
            directory = self.root / name
            if not directory.exists() and not directory.is_symlink():
                rows.append({"name": name, "status": "not installed"})
                continue
            try:
                current = self.enroll(item)
                _, latest = self.latest(item)
                rows.append({"name": name, "status": "current" if current == latest else "update available"})
            except (Failure, OSError, ValueError, yaml.YAMLError) as exc:
                rows.append({"name": name, "status": "skipped / freshness unknown", "reason": str(exc)})
                # Pins, edits, and unmanaged installs are not failures of the network check.
                # Still throttle incomplete attempts only one hour, rather than claiming freshness.
                complete = False
        check = {"time": now, "complete": complete, "results": rows, "files": self.installed_fingerprints()}
        self.state["check"] = check
        self.save()
        return {"cached": False, **check}

    def installed_fingerprints(self):
        result = {}
        for name in self.catalog:
            directory = self.root / name
            if directory.exists() or directory.is_symlink():
                try:
                    result[name] = fingerprint(directory)
                except Failure:
                    result[name] = "unmanaged filesystem object"
        return result

    def install(self, name, update=False):
        item = self.catalog[name]
        destination = self.root / name
        present = destination.exists() or destination.is_symlink()
        if present and not update:
            return {"name": name, "status": "already installed; read existing instructions", "path": str(destination)}
        if not present and update:
            return {"name": name, "status": "not installed; left absent"}
        before = None
        if present:
            current = self.enroll(item)
            before = fingerprint(destination)
        commit, tree = self.latest(item)
        if present and current == tree:
            return {"name": name, "status": "current"}
        self.root.mkdir(parents=True, exist_ok=True)
        # Stage on the destination filesystem so rename is atomic and works across cache mounts.
        with tempfile.TemporaryDirectory(prefix=".braingeneers-stage-", dir=self.root) as stage:
            command(["gh", "skill", "install", item["repo"], item["path"] + "@" + commit,
                     "--dir", stage], cwd=stage)
            staged = Path(stage) / name
            meta = self.metadata(item, staged)
            if meta["github-tree-sha"] != tree:
                raise Failure("Downloaded skill does not match the resolved source tree.")
            self.verify(item, staged, tree)
            downloaded = fingerprint(staged)
            backup = None
            if present:
                if fingerprint(destination) != before:
                    raise Failure("Installation changed while downloading; left unchanged.")
                # Keep backups outside application discovery; rename fails safely across filesystems.
                backups = self.root.parent / ".braingeneers-one-backups"
                backups.mkdir(exist_ok=True)
                root_id = hashlib.sha256(str(self.root).encode()).hexdigest()[:16]
                backup = backups / (root_id + "-" + name + "-" + str(time.time_ns()))
                destination.rename(backup)
            elif destination.exists() or destination.is_symlink():
                raise Failure("Installation appeared while downloading; left unchanged.")
            try:
                staged.rename(destination)
            except OSError:
                if backup:
                    backup.rename(destination)
                raise
        self.state["managed"][name] = {"files": downloaded, "tree": tree}
        self.state.pop("check", None)
        self.save()
        result = {"name": name, "status": "updated" if present else "installed", "path": str(destination)}
        if backup:
            result["backup"] = str(backup)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, help="Override the router's installation root")
    parser.add_argument("--state-dir", type=Path, help="Override the root-specific state directory")
    sub = parser.add_subparsers(dest="operation", required=True)
    status = sub.add_parser("status", help="Check installed suite members without updating")
    status.add_argument("--daily", action="store_true", help="Reuse a recent check")
    install = sub.add_parser("install", help="Install one missing catalog member")
    install.add_argument("name")
    update = sub.add_parser("update", help="Apply requested updates to installed suite members")
    update.add_argument("names", nargs="*")
    args = parser.parse_args()
    root = (args.skills_dir or ONE.parent).expanduser().absolute()
    # Resolving __file__ loses a symlink's installation context; do not infer placement in a checkout.
    if args.skills_dir is None and root.name != "skills":
        parser.error("Nonstandard source location: specify --skills-dir explicitly.")
    if args.skills_dir is None and (ONE.parent.parent / ".git").exists():
        parser.error("Source checkout: specify the application's --skills-dir explicitly.")
    root_id = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    state_dir = (args.state_dir or cache / "braingeneers-one" / root_id).expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "running.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        sys.exit(f"Another helper may be running. If it was interrupted, verify it stopped, then trash {lock}.")
    suite = None
    try:
        suite = Suite(root, state_dir)
        if args.operation == "status":
            output = suite.status(args.daily)
        else:
            names = [args.name] if args.operation == "install" else (args.names or list(suite.catalog))
            unknown = set(names) - suite.catalog.keys()
            if unknown:
                raise Failure("Not in the approved catalog: " + ", ".join(sorted(unknown)))
            names = sorted(set(names), key=lambda name: (name == "braingeneers-one", name))
            output = []
            for name in names:
                try:
                    output.append(suite.install(name, update=args.operation == "update"))
                except (Failure, OSError, ValueError, yaml.YAMLError) as exc:
                    output.append({"name": name, "status": "skipped / failed", "reason": str(exc)})
        # Fingerprints stay internal; output is bounded and useful for agents and people.
        public = {key: value for key, value in output.items() if key != "files"} if isinstance(output, dict) else output
        print(json.dumps(public, indent=2))
        failed = (not output.get("complete", False)) if isinstance(output, dict) else any(row["status"] == "skipped / failed" for row in output)
        return 1 if failed else 0
    except (Failure, OSError, ValueError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        try:
            if suite:
                suite.save()
        finally:
            lock.rmdir()


if __name__ == "__main__":
    sys.exit(main())
