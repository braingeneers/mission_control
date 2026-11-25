#!/usr/bin/env python3
"""Maintain only cataloged Braingeneers skills; never run lab operations."""

import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
import plistlib
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

# Load the bundled pure Python reader independently of site-packages or an
# already imported 'yaml'. Imports must not add files to verified skill trees.
_yaml_spec = importlib.util.spec_from_file_location(
    "_braingeneers_one_yaml", Path(__file__).parent / "_vendor/yaml/__init__.py")
yaml = importlib.util.module_from_spec(_yaml_spec)
sys.modules[_yaml_spec.name] = yaml
_previous_dont_write_bytecode = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    _yaml_spec.loader.exec_module(yaml)
finally:
    sys.dont_write_bytecode = _previous_dont_write_bytecode


ONE = Path(__file__).resolve().parents[1]
TRACKING = {"github-repo", "github-ref", "github-tree-sha", "github-path", "github-pinned"}


class Failure(Exception):
    pass


class Unmanaged(Failure):
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


def files_at(directory, local_links=False):
    if directory.is_symlink() or not directory.is_dir():
        raise Failure("Symlink or non-directory installation; preserve and maintain through its owner.")
    files = {}
    for item in directory.rglob("*"):
        if item.is_symlink():
            if local_links:
                files[item.relative_to(directory).as_posix()] = None
                continue
            raise Failure("Contains a symlink; preserve and maintain through its owner.")
        if item.is_dir():
            continue
        if not item.is_file():
            raise Failure("Contains an unsupported filesystem object.")
        files[item.relative_to(directory).as_posix()] = item.read_bytes()
    return files


def fingerprint(directory, local_links=False):
    return {name: hashlib.sha256(data).hexdigest() if data is not None else
            "symlink:" + os.readlink(directory / name)
            for name, data in files_at(directory, local_links).items()}


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
            raise Unmanaged("Explicitly pinned; left unchanged.")
        repo = str(meta.get("github-repo", "")).rstrip("/")
        if repo.endswith(".git"):
            repo = repo[:-4]
        if (header.get("name") != item["name"]
                or repo != "https://github.com/" + item["repo"]
                or meta.get("github-path") != item["path"]
                or not re.fullmatch(r"[0-9a-f]{40}", str(meta.get("github-tree-sha", "")))):
            raise Unmanaged("Unknown source or path; left unchanged.")
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
            raise Unmanaged("Local files added or missing; left unchanged.")
        for name, entry in expected.items():
            if entry["type"] != "blob" or entry["mode"] not in ("100644", "100755"):
                raise Unmanaged("Unsupported upstream object; left unchanged.")
            if Path(name).name == "SKILL.md":
                upstream = api(f"repos/{item['repo']}/git/blobs/{entry['sha']}")
                original_header, original_body = frontmatter(base64.b64decode(upstream["content"]))
                local_header, local_body = frontmatter(local[name])
                if without_tracking(local_header) != without_tracking(original_header) or local_body != original_body:
                    raise Unmanaged("Local instructions modified; left unchanged.")
            elif blob_sha(local[name]) != entry["sha"]:
                raise Unmanaged("Local files modified; left unchanged.")

    def enroll(self, item):
        directory = self.root / item["name"]
        current = fingerprint(directory)
        meta = self.metadata(item, directory)
        recorded = self.state["managed"].get(item["name"])
        if recorded:
            if recorded["files"] != current or recorded["tree"] != meta["github-tree-sha"]:
                raise Unmanaged("Changed since last managed installation; left unchanged.")
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

    def entries(self):
        local = {path.name for path in self.root.iterdir()} if self.root.exists() else set()
        return sorted((local | self.catalog.keys()) - {"synced"})

    def link_status(self, destination):
        link = Path.home() / ".agents/skills" / destination.name
        return ("ok" if link.is_symlink() and (link / "SKILL.md").is_file()
                and link.resolve() == destination.resolve() else "missing")

    def local_status(self, name):
        destination = self.root / name
        item = self.catalog.get(name, {})
        row = {"name": name, "source": item.get("repo", "-"), "state": "n/a",
               "codex_link": self.link_status(destination)}
        if destination.is_symlink():
            row["source"] = os.readlink(destination)
            if destination.exists():
                row["mode"] = "external link"
            else:
                row.update(mode="dangling link", state="stuck",
                           reason="DANGLING LINK. Restore its target or repair the link.")
        elif not destination.exists():
            row["mode"] = "not installed"
        elif not destination.is_dir():
            row["mode"] = "unmanaged file"
        elif name not in self.state["managed"] or not item:
            row["mode"] = "unmanaged dir"
        elif fingerprint(destination, local_links=True) != self.state["managed"][name]["files"]:
            row.update(mode="modified copy", state="stuck",
                       reason=f"Local edits prevent all updates. Run suite.py reset {name} to back them up and reinstall.")
        else:
            row["mode"] = "managed copy"
        return row

    def status(self, daily=False):
        now = time.time()
        cache = self.state.get("check", {})
        interval = 86400 if cache.get("complete") else 3600
        snapshot = self.installed_fingerprints()
        if daily and 0 <= now - cache.get("time", 0) < interval and cache.get("files") == snapshot:
            return {"cached": True, **cache}
        rows, complete = [], True
        for name in self.entries():
            row = {"name": name, "mode": "unmanaged dir", "state": "n/a",
                   "source": self.catalog.get(name, {}).get("repo", "-"), "codex_link": "missing"}
            try:
                row = self.local_status(name)
                if name in self.catalog and row["mode"] in ("managed copy", "unmanaged dir"):
                    # Bootstrap pristine gh installs, including the router. Auto updates
                    # only use existing records and never perform this enrollment.
                    try:
                        current = self.enroll(self.catalog[name])
                    except Unmanaged as exc:
                        row["reason"] = str(exc)
                    else:
                        row["mode"] = "managed copy"
                        _, latest = self.latest(self.catalog[name])
                        row["state"] = "current" if current == latest else "behind"
            except OPERATION_ERRORS as exc:
                complete = False
                row["reason"] = str(exc)
                row["status"] = "skipped / freshness unknown"
            row.setdefault("status", {"behind": "update available", "current": "current"}
                           .get(row["state"], row["mode"]))
            rows.append(row)
        check = {"time": now, "complete": complete, "results": rows, "files": snapshot}
        self.state["check"] = check
        self.save()
        return {"cached": False, **check}

    def installed_fingerprints(self):
        result = {}
        for name in self.entries():
            path = self.root / name
            entry = {"codex_link": self.link_status(path)}
            if path.is_symlink():
                entry.update(target=os.readlink(path), exists=path.exists())
            elif path.is_dir() and name in self.catalog:
                try:
                    entry["files"] = fingerprint(path, local_links=True)
                except (Failure, OSError):
                    entry["files"] = None
            elif path.exists():
                entry["type"] = "dir" if path.is_dir() else "file"
            result[name] = entry
        return result

    def codex_link(self, destination):
        """Expose the canonical Claude Code install to Codex."""
        home = Path.home()
        if self.root != home / ".claude/skills" or not (destination / "SKILL.md").is_file():
            return {}
        link = home / ".agents/skills" / destination.name
        try:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(destination, target_is_directory=True)
        except FileExistsError:
            if not link.is_symlink() or Path(os.path.abspath(link.parent / os.readlink(link))) != destination:
                return {"codex_link_note": f"Existing path preserved: {link}"}
        except OSError as exc:
            return {"codex_link_error": f"Could not create {link}: {exc}"}
        return {"codex_link": str(link)}

    def install(self, name, update=False, reset=False, auto=False):
        item = self.catalog[name]
        destination = self.root / name
        present = destination.exists() or destination.is_symlink()
        if reset:
            if self.local_status(name)["mode"] != "modified copy":
                raise Failure("Reset requires a modified managed copy.")
        elif present and not update:
            return {"name": name, "status": "already installed; read existing instructions",
                    "path": str(destination), **self.codex_link(destination)}
        if not present and update:
            return {"name": name, "status": "not installed; left absent"}
        before = None
        if present:
            original = destination.lstat()
            before = fingerprint(destination, local_links=reset)
            if not reset:
                current = self.enroll(item)
        commit, tree = self.latest(item)
        if present and not reset and current == tree:
            return {"name": name, "status": "current",
                    **({} if auto else self.codex_link(destination))}
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
                if (not os.path.samestat(original, destination.lstat())
                        or fingerprint(destination, local_links=reset) != before):
                    raise Failure("Installation changed while downloading; left unchanged.")
                # Keep backups outside application discovery; rename fails safely across filesystems.
                backups = (self.state_dir / "backups" if reset else
                           self.root.parent / ".braingeneers-one-backups")
                backups.mkdir(parents=True, exist_ok=True)
                root_id = hashlib.sha256(str(self.root).encode()).hexdigest()[:16]
                backup = backups / (root_id + "-" + name + "-" + str(time.time_ns()))
                if reset:
                    diff = backup.with_suffix(".diff.txt")
                    managed = self.state["managed"][name]["files"]
                    changes = [
                        f"{'added' if path not in managed else 'removed' if path not in before else 'modified'} {path!r}"
                        for path in sorted(before.keys() | managed.keys()) if before.get(path) != managed.get(path)
                    ]
                    diff.write_text("\n".join(changes) + "\n")
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
        result = {"name": name, "status": "reset" if reset else "updated" if present else "installed",
                  "path": str(destination)}
        if reset:
            result["diff_summary"] = str(diff)
        if backup:
            result["backup"] = str(backup)
        if not auto:
            result.update(self.codex_link(destination))
        return result


SCHEDULE_LABEL = "org.braingeneers.one-update"
OPERATION_ERRORS = (Failure, OSError, ValueError, KeyError, yaml.YAMLError)


def scheduler_command(args, check=False):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if check and result.returncode:
        raise Failure(f"Scheduler command failed: {' '.join(args[:3])}. Check your user scheduler.")
    return result.returncode == 0


def schedule(action, root, state_dir):
    home = Path.home()
    runner = root / "braingeneers-one/scripts/suite.py"
    argv = [sys.executable, str(runner), "--skills-dir", str(root),
            "--state-dir", str(state_dir), "update", "--auto"]
    environment = {key: os.environ[key] for key in ("PATH", "GH_CONFIG_DIR", "XDG_CONFIG_HOME")
                   if key in os.environ}
    ensure = action == "ensure"
    if ensure:
        action = "enable"
    if action == "enable" and not runner.is_file():
        raise Failure(f"Install Braingeneers One at {runner.parent.parent} before enabling the schedule.")

    def cron_fallback(reason):
        command_line = shlex.join(["env", *(f"{key}={value}" for key, value in environment.items()), *argv])
        return reason + " Add this line with crontab -e:\n0 9 * * * " + command_line.replace("%", r"\%")

    if sys.platform == "darwin":
        path = home / "Library/LaunchAgents" / (SCHEDULE_LABEL + ".plist")
        domain = f"gui/{os.getuid()}"
        target = f"{domain}/{SCHEDULE_LABEL}"
        try:
            loaded = scheduler_command(["launchctl", "print", target])
            if action == "enable" and not loaded and not scheduler_command(["launchctl", "print", domain]):
                return cron_fallback("User launchd session unavailable.")
        except FileNotFoundError:
            if action == "enable":
                return cron_fallback("launchctl unavailable.")
            if action == "disable":
                path.unlink(missing_ok=True)
            loaded = False
        if ensure and loaded:
            return None
        if action == "status":
            return "Daily updates enabled." if loaded else "Daily updates disabled."
        if loaded:
            scheduler_command(["launchctl", "bootout", target], check=True)
        if action == "enable":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(plistlib.dumps({
                "Label": SCHEDULE_LABEL,
                "ProgramArguments": argv,
                "EnvironmentVariables": environment,
                "StartCalendarInterval": {"Hour": 9, "Minute": 0},
                "StandardOutPath": str(state_dir / "auto.log"),
                "StandardErrorPath": str(state_dir / "auto-errors.log"),
            }))
            scheduler_command(["launchctl", "bootstrap", domain, str(path)], check=True)
        else:
            path.unlink(missing_ok=True)
    elif sys.platform.startswith("linux"):
        unit_dir = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "systemd/user"
        service = unit_dir / (SCHEDULE_LABEL + ".service")
        timer = unit_dir / (SCHEDULE_LABEL + ".timer")
        systemctl = ["systemctl", "--user"]
        try:
            available = scheduler_command(systemctl + ["show-environment"])
        except FileNotFoundError:
            available = False
        if not available:
            if action == "enable":
                return cron_fallback("User systemd unavailable.")
            if action == "disable" and timer.exists():
                raise Failure("User systemd unavailable. Restore access to your user manager and retry disabling the timer.")
            return "User systemd unavailable. Inspect crontab -l or remove the update line with crontab -e."
        if action == "status" or ensure:
            enabled = scheduler_command(systemctl + ["is-enabled", "--quiet", timer.name])
            active = scheduler_command(systemctl + ["is-active", "--quiet", timer.name])
            if action == "status":
                return "Daily updates enabled." if enabled and active else "Daily updates disabled."
            if enabled and active:
                return None
        if action == "enable":
            unit_dir.mkdir(parents=True, exist_ok=True)
            # systemd performs its own specifier and environment expansion.
            quoted = [json.dumps(arg.replace("%", "%%").replace("$", "$$"), ensure_ascii=False) for arg in argv]
            settings = "".join("Environment=" + json.dumps(f"{key}={value}".replace("%", "%%"),
                                                           ensure_ascii=False) + "\n"
                               for key, value in environment.items())
            service.write_text("[Service]\nType=oneshot\n" + settings + "ExecStart=" + " ".join(quoted) + "\n")
            timer.write_text("[Timer]\nOnCalendar=*-*-* 09:00:00\nPersistent=true\n[Install]\nWantedBy=timers.target\n")
            scheduler_command(systemctl + ["daemon-reload"], check=True)
            scheduler_command(systemctl + ["enable", "--now", timer.name], check=True)
        elif timer.exists():
            scheduler_command(systemctl + ["disable", "--now", timer.name], check=True)
            timer.unlink()
            service.unlink(missing_ok=True)
            scheduler_command(systemctl + ["daemon-reload"], check=True)
    else:
        raise Failure("Scheduling is supported on macOS and Linux.")
    return "Daily updates enabled." if action == "enable" else "Daily updates disabled."


def print_status_table(output):
    rows = [["NAME", "MODE", "SOURCE", "STATE", "CODEX LINK"]]
    rows.extend([row[key] for key in ("name", "mode", "source", "state", "codex_link")]
                for row in output["results"])
    widths = [max(map(len, column)) for column in zip(*rows)]
    for row in rows:
        print("  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())
    for row in output["results"]:
        if row.get("reason"):
            print(f"{row['name']}: {row['reason']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, help="Override the router's installation root")
    parser.add_argument("--state-dir", type=Path, help="Override the root-specific state directory")
    sub = parser.add_subparsers(dest="operation", required=True)
    status = sub.add_parser("status", help="Check installed suite members without updating")
    status.add_argument("--daily", action="store_true", help="Reuse a recent check")
    status_format = status.add_mutually_exclusive_group()
    status_format.add_argument("--json", action="store_true", help="Print JSON (default)")
    status_format.add_argument("--table", action="store_true", help="Print a human-readable table")
    install = sub.add_parser("install", help="Install one missing catalog member")
    install.add_argument("name")
    update = sub.add_parser("update", help="Apply requested updates to installed suite members")
    update.add_argument("names", nargs="*")
    update.add_argument("--auto", action="store_true", help="Quietly update unmodified managed copies")
    reset = sub.add_parser("reset", help="Back up a modified managed copy and reinstall")
    reset.add_argument("name")
    scheduling = sub.add_parser("schedule", help="Manage the daily update job")
    scheduling.add_argument("action", choices=("enable", "disable", "status"))
    args = parser.parse_args()
    auto = args.operation == "update" and args.auto
    if auto and args.names:
        parser.error("update --auto checks all managed skills and accepts no names.")
    root = (args.skills_dir or ONE.parent).expanduser().absolute()
    # Resolving __file__ loses a symlink's installation context; do not infer placement in a checkout.
    if args.skills_dir is None and root.name != "skills":
        parser.error("Nonstandard source location: specify --skills-dir explicitly.")
    if args.skills_dir is None and (ONE.parent.parent / ".git").exists():
        parser.error("Source checkout: specify the application's --skills-dir explicitly.")
    root_id = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    state_dir = (args.state_dir or cache / "braingeneers-one" / root_id).expanduser().absolute()
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "running.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        if auto:
            return 0
        sys.exit(f"Another helper may be running. If it was interrupted, verify it stopped, then trash {lock}.")
    suite = None
    opt_out = state_dir / "auto-update-disabled"
    try:
        if args.operation == "schedule":
            if args.action == "disable":
                opt_out.touch()
            print(schedule(args.action, root, state_dir))
            if args.action == "enable":
                opt_out.unlink(missing_ok=True)
            return 0
        if auto and opt_out.exists():
            return 0
        suite = Suite(root, state_dir)
        if args.operation == "status":
            output = suite.status(args.daily)
            if args.table:
                print_status_table(output)
            else:
                print(json.dumps({key: value for key, value in output.items() if key != "files"}, indent=2))
            return 0 if output["complete"] else 1
        else:
            names = [args.name] if args.operation in ("install", "reset") else (args.names or list(suite.catalog))
            unknown = set(names) - suite.catalog.keys()
            if unknown:
                raise Failure("Not in the approved catalog: " + ", ".join(sorted(unknown)))
            names = sorted(set(names), key=lambda name: (name == "braingeneers-one", name))
            output = []
            for name in names:
                try:
                    if auto and (name not in suite.state["managed"]
                                 or suite.local_status(name)["mode"] != "managed copy"):
                        continue
                    output.append(suite.install(name, update=args.operation == "update",
                                                reset=args.operation == "reset", auto=auto))
                except OPERATION_ERRORS as exc:
                    output.append({"name": name, "status": "skipped / failed", "reason": str(exc)})
        errors = [(row["name"], row.get("reason") or row["codex_link_error"])
                  for row in output if row["status"] == "skipped / failed" or row.get("codex_link_error")]
        if auto:
            updated = [row["name"] for row in output if row["status"] == "updated"]
            if updated:
                print("Updated Braingeneers skills: " + ", ".join(updated))
            for name, reason in errors:
                print(f"{name}: {reason}", file=sys.stderr)
        else:
            print(json.dumps(output, indent=2))
        if (not auto and args.operation in ("install", "update") and not opt_out.exists()
                and (sys.platform == "darwin" or sys.platform.startswith("linux"))
                and (root / "braingeneers-one/scripts/suite.py").is_file()):
            message = schedule("ensure", root, state_dir)
            if message:
                print(message, file=sys.stderr)
        return 1 if errors else 0
    except OPERATION_ERRORS + (subprocess.TimeoutExpired,) as exc:
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
