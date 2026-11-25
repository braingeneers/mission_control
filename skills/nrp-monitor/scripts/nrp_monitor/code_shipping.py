"""Content-addressed code bundles for registered NRP tasks."""
import fnmatch
import gzip
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from . import config, s3, state
from .task import registry

URI_ENV = "NRP_CODE_URI"
SHA_ENV = "NRP_CODE_SHA256"
TAR_SHA_ENV = "NRP_CODE_TAR_SHA256"
ADAPTERS = ("generic", "pv3")
REPO_ENV = "NRP_CODE_REPO"
COMMIT_ENV = "NRP_CODE_COMMIT"
DIRTY_ENV = "NRP_CODE_DIRTY"
DIRS_ENV = "NRP_CODE_DIRS"
REMOTE_ENV = "NRP_CODE_REMOTE"
BRANCH_ENV = "NRP_CODE_BRANCH"
PUSHED_ENV = "NRP_CODE_PUSHED"
ENV_NAMES = (URI_ENV, SHA_ENV, TAR_SHA_ENV, REPO_ENV, COMMIT_ENV, DIRTY_ENV, DIRS_ENV, REMOTE_ENV, BRANCH_ENV, PUSHED_ENV)
DENIED = ("kubeconfig*", "*.pem", "*.key", "id_*", "credentials*.json", "token*.json",
          ".env*", "*.p12", "service-account*.json", ".aws", ".ssh", ".netrc")
SKIP_NAMES = {*state.CODE_SKIP, ".aws", ".env", ".ssh", ".netrc"}


def validate_prefix(prefix):
    if (not isinstance(prefix, str) or not re.fullmatch(r"s3://[a-z0-9.-]+/[A-Za-z0-9._/-]+", prefix)
            or any(part in (".", "..") for part in prefix.split("/")[3:])
            or prefix.rstrip("/") == "s3://braingeneerscache/braindance"
            or prefix.startswith("s3://braingeneerscache/braindance/")):
        raise ValueError("code bundle prefix must be an S3 directory outside braingeneerscache/braindance/")
    return prefix.rstrip("/")


def bundle_prefix(code):
    prefix = code.get("bundle_prefix") or state.OWNER.get("code_bundle_prefix")
    if not prefix:
        owner = state.nrp_username()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", owner):
            raise state.ChainError("configure code_bundle_prefix for this owner label")
        prefix = "s3://braingeneerscache/nrp-monitor/code/" + owner
    return validate_prefix(prefix)


def shipping_adapter(code, manifest=None):
    """Honor explicit configuration, then recognize old registrations."""
    if code.get("adapter") == "generic" or (not code.get("adapter") and code.get("dirs")):
        return None
    from .adapters import pv3

    if code.get("adapter") == "pv3":
        return pv3
    if manifest and code_container(registry.manifest_doc(manifest), required=False) is not None:
        return None
    return pv3 if pv3.matches(code, manifest) else None


def code_dirs(code, override=None):
    """Resolve declared paths inside the clone, retaining their clone-relative layout."""
    clone = Path(code["clone"]).resolve()
    requested = [override] if override is not None else code.get("dirs") or [code.get("subdir") or "."]
    paths = []
    for name in requested:
        rel = Path(name)
        source = clone / rel
        if rel.is_absolute() or ".." in rel.parts or not source.is_dir() or source.resolve() != source:
            raise state.ChainError("code directory %s must be a folder inside the clone without symlinks" % name)
        paths.append(rel)
    return clone, paths


def excluded(path):
    return bool(SKIP_NAMES.intersection(path.parts)) or path.name.endswith(state.CODE_SKIP_EXT)


def denied(path):
    return any(fnmatch.fnmatchcase(part.lower(), pattern) for part in path.parts for pattern in DENIED)


def reject_denied(paths):
    for path in paths:
        if denied(Path(path)):
            raise state.ChainError("refusing to ship credential-like path %s" % path)


def stream_sha256(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def pack(clone, commit, dirs, archive):
    """Pack regular Git blobs with normalized tar and gzip headers."""
    paths = [] if Path(".") in dirs else [p.as_posix() for p in dirs]
    tree = subprocess.run(["git", "--literal-pathspecs", "ls-tree", "-r", "-z", "-l", commit, "--", *paths],
                          cwd=clone, capture_output=True, timeout=120)
    if tree.returncode:
        raise state.ChainError("could not list code files from the recorded commit")
    files = []
    for record in tree.stdout.split(b"\0")[:-1]:
        header, raw_name = record.split(b"\t", 1)
        mode, kind, oid, size = header.split()
        name = os.fsdecode(raw_name)
        reject_denied([name])
        if kind == b"blob" and mode in (b"100644", b"100755") and not excluded(Path(name)):
            files.append((name, oid, int(size), int(mode, 8) & 0o777))
    if not files:
        raise state.ChainError("no regular code files in the selected Git directories")
    limit = state.CODE_SNAPSHOT_MAX
    if sum(item[2] for item in files) > limit:
        raise state.ChainError("unpacked code exceeds %d MiB" % (limit // 2**20))
    files.sort()
    with tempfile.TemporaryFile() as blobs:
        result = subprocess.run(["git", "cat-file", "--batch"], cwd=clone,
                                input=b"".join(oid + b"\n" for _, oid, _, _ in files),
                                stdout=blobs, stderr=subprocess.PIPE, timeout=120)
        if result.returncode:
            raise state.ChainError("could not read code blobs from the recorded commit")
        blobs.seek(0)
        with archive.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as bundle:
                for name, oid, size, mode in files:
                    if blobs.readline().split() != [oid, b"blob", str(size).encode()]:
                        raise state.ChainError("unexpected Git blob for %s" % name)
                    member = tarfile.TarInfo(name)
                    member.size, member.mode = size, mode
                    bundle.addfile(member, blobs)
                    if blobs.read(1) != b"\n":
                        raise state.ChainError("incomplete Git blob for %s" % name)
    if archive.stat().st_size > limit:
        raise state.ChainError("code archive exceeds %d MiB" % (limit // 2**20))
    with gzip.open(archive, "rb") as uncompressed:
        tar_hash = stream_sha256(uncompressed)
    with archive.open("rb") as compressed:
        return stream_sha256(compressed), tar_hash


def upload_code_archive(path, uri):
    result = subprocess.run(registry.aws_cmd() + ["s3", "cp", str(path), uri],
                            capture_output=True, text=True, timeout=300, env=config.aws_env())
    if result.returncode:
        raise state.ChainError("upload of the code tarball failed: %s" % result.stderr.strip()[:200])


def git_at(clone, *args, index=None):
    """Use the task clone's Git identity and suppress interactive credential prompts."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    return subprocess.run(["git", *state.GIT_ID, *args], cwd=clone, capture_output=True,
                          text=True, timeout=120, env=env)


def checked_git(clone, message, *args, index=None):
    result = git_at(clone, *args, index=index)
    if result.returncode:
        raise state.ChainError(message)
    return result.stdout if "-z" in args else result.stdout.strip()


def push_remote(code):
    # Task clones use the local source checkout as origin. Follow local origins for continuations.
    source = Path(code["repo"]).resolve()
    seen = set()
    while source.is_dir() and source not in seen:
        seen.add(source)
        remote = checked_git(source, "source repository has no push remote configured", "remote", "get-url", "--push", "origin")
        if "://" in remote:
            parsed = urlsplit(remote)
            if parsed.password or parsed.query or parsed.fragment or (parsed.scheme in ("http", "https") and parsed.username):
                raise state.ChainError("configure Git credentials outside the source remote URL")
            return remote
        if re.match(r"^(?:[^@/:]+@)?[^/:]+:", remote):
            return remote
        target = (source / remote).resolve()
        # Continue through monitor clones only. A local bare upstream is a valid push remote.
        if not target.is_relative_to(state.TASK_CACHE.resolve()):
            return str(target)
        source = target
    raise state.ChainError("source repository has no usable push remote")


def remote_ref(task):
    code = task["code"]
    prefix = code.get("branch_prefix") or state.OWNER.get("code_branch_prefix") or "nrp-tasks"
    if not isinstance(prefix, str) or not prefix.strip("/"):
        raise state.ChainError("code branch prefix must name a Git ref directory")
    ref = "refs/heads/%s/%s/%s" % (prefix.strip("/"), state.nrp_username(), task["name"])
    checked_git(code["clone"], "invalid code branch prefix", "check-ref-format", ref)
    return ref


def commit_code(task, label, clone, dirs, additions=(), archive=None):
    code = task["code"]
    branch = checked_git(clone, "shipping requires a Git task clone on its task branch",
                         "symbolic-ref", "--short", "HEAD")
    if branch != code.get("branch"):
        raise state.ChainError("checkout the task's branch before shipping")
    scope = [p.as_posix() for p in dirs]
    tracked = set(checked_git(clone, "could not list tracked code", "--literal-pathspecs", "ls-tree", "-r", "-z", "--name-only",
                              "HEAD", "--", *scope).split("\0")) - {""}
    reject_denied(sorted(tracked))
    declared = set()
    for name in additions:
        path = Path(name)
        source = clone / path
        reject_denied([path])
        if (path.is_absolute() or ".." in path.parts or source.resolve() != source
                or not source.is_file() or not any(path.is_relative_to(d) for d in dirs) or excluded(path)):
            raise state.ChainError("--add requires a regular file inside the selected code directories: %s" % name)
        declared.add(path.as_posix())
    selected = sorted(p for p in tracked | declared if not excluded(Path(p)))
    total = sum((clone / p).stat().st_size for p in selected
                if (clone / p).is_file() and (clone / p).resolve() == clone / p)
    if total > state.CODE_SNAPSHOT_MAX:
        raise state.ChainError("unpacked code exceeds %d MiB" % (state.CODE_SNAPSHOT_MAX // 2**20))
    changed = set(checked_git(clone, "could not inspect tracked changes", "--literal-pathspecs", "diff", "HEAD", "--no-renames", "--name-only",
                              "-z", "--", *scope).split("\0"))
    paths = sorted((set(selected) & changed) | declared)
    hashes = None
    if paths:
        # Check the exact archive size before committing, including tar and gzip overhead.
        # Keep the user's existing index out of the candidate tree.
        with tempfile.TemporaryDirectory(prefix="nrp-code-index-") as tmp:
            index = Path(tmp) / "index"
            checked_git(clone, "could not initialize code size check", "read-tree", "HEAD", index=index)
            tracked_paths = sorted(set(paths) - declared)
            if tracked_paths:
                checked_git(clone, "could not stage tracked paths in the code size check",
                            "--literal-pathspecs", "add", "-u", "--", *tracked_paths, index=index)
            if declared:
                checked_git(clone, "could not stage declared paths in the code size check",
                            "--literal-pathspecs", "add", "--", *sorted(declared), index=index)
            tree = checked_git(clone, "could not build code tree for the size check", "write-tree", index=index)
            hashes = pack(clone, tree, dirs, archive if archive is not None else Path(tmp) / "code.tgz")
        if declared:
            checked_git(clone, "could not stage explicitly declared files", "--literal-pathspecs",
                        "add", "--", *sorted(declared))
        actor = os.environ.get("NRP_MONITOR_AGENT_ROLE") or state.OWNER_NAME
        message = "NRP code for %s/%s, prepared by %s" % (task["name"], label, actor)
        checked_git(clone, "could not commit selected changes", "--literal-pathspecs",
                    "commit", "-qm", message, "--only", "--", *paths)
    commit = checked_git(clone, "could not read task code commit", "rev-parse", "--verify", "HEAD")
    if paths:
        committed_tree = checked_git(clone, "could not verify committed code tree", "rev-parse", "HEAD^{tree}")
        if committed_tree != tree:
            raise state.ChainError("the code changed during shipping; review the task clone and ship again")
    elif archive is not None:
        hashes = pack(clone, commit, dirs, archive)
    return commit, hashes


def bundle_fresh(uri):
    bucket, key = s3.s3_split(uri)
    result = subprocess.run(registry.aws_cmd() + ["s3api", "head-object", "--bucket", bucket, "--key", key,
                                                  "--output", "json"], capture_output=True, text=True,
                            timeout=120, env=config.aws_env())
    if result.returncode:
        if "(404)" in result.stderr and "HeadObject" in result.stderr:
            return False
        raise state.ChainError("could not verify code bundle " + uri)
    try:
        modified = datetime.fromisoformat(json.loads(result.stdout)["LastModified"].replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - modified <= timedelta(days=30)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise state.ChainError("could not verify code bundle age " + uri) from exc


def provenance_tag(task, stage):
    return "refs/tags/nrp-run/%s/%s/%s" % (state.nrp_username(), task["name"], stage)


def publish(task, label, override=None, *, allow_unpushed=False, additions=()):
    code = task.get("code")
    if not code:
        raise state.ChainError("this task has no code clone")
    clone, dirs = code_dirs(code, override)
    prefix = bundle_prefix(code)
    ref = remote_ref(task)
    remote = ""
    pushed = False
    with tempfile.TemporaryDirectory(prefix="nrp-ship-") as tmp:
        archive = Path(tmp) / "code.tgz"
        commit, (sha, tar_sha) = commit_code(task, label, clone, dirs, additions, archive)
        if code.get("base"):
            changed = checked_git(clone, "could not audit task commit history", "log", "--format=", "--no-renames",
                                  "--name-only", "-z", code["base"] + ".." + commit)
            reject_denied(sorted(set(changed.split("\0")) - {""}))
        try:
            remote = push_remote(code)
            checked_git(clone, "could not push the task branch (check Git write access, authentication and branch history)",
                        "push", "--", remote, commit + ":" + ref)
            pushed = True
        except (state.ChainError, subprocess.TimeoutExpired) as exc:
            if not allow_unpushed:
                raise state.ChainError("%s; --allow-unpushed is for debug runs only" % exc) from exc
        if pushed:
            state.task_txn(task["name"], lambda t: t.setdefault("code_remote_heads", {}).setdefault(remote, {}).update({ref: commit}))
        uri = "%s/%s.tgz" % (prefix, sha)
        if not bundle_fresh(uri):
            upload_code_archive(archive, uri)
    return {URI_ENV: uri, SHA_ENV: sha, TAR_SHA_ENV: tar_sha, COMMIT_ENV: commit,
            REMOTE_ENV: remote, BRANCH_ENV: ref, PUSHED_ENV: str(pushed).lower(), DIRTY_ENV: str(not pushed).lower(),
            DIRS_ENV: json.dumps([p.as_posix() for p in dirs], separators=(",", ":"))}


def ensure_bundle(task, stage, doc):
    """Check availability before submit and recover the exact archive from its recorded commit."""
    container = code_container(doc, required=False)
    if container is None:
        return None
    container["env"] = [entry for entry in container["env"] if entry.get("name") != REPO_ENV]
    info = {e["name"]: e.get("value") for e in container["env"] if e.get("name") in ENV_NAMES}
    uri, sha, commit = (info.get(key) for key in (URI_ENV, SHA_ENV, COMMIT_ENV))
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise state.ChainError("%s must be a literal SHA-256" % SHA_ENV)
    if not isinstance(uri, str) or not uri.endswith("/" + sha + ".tgz"):
        raise state.ChainError("%s must end in /<sha256>.tgz" % URI_ENV)
    validate_prefix(uri.rsplit("/", 1)[0])
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise state.ChainError("Job must declare a full %s from nrp-task ship" % COMMIT_ENV)
    if info.get(PUSHED_ENV) not in ("true", "false") or info.get(DIRTY_ENV) != str(info[PUSHED_ENV] == "false").lower():
        raise state.ChainError("Job must declare the Git push status printed by nrp-task ship")
    if info[PUSHED_ENV] == "true" and not info.get(REMOTE_ENV):
        raise state.ChainError("Job must declare the Git push remote printed by nrp-task ship")
    tar_sha = info.get(TAR_SHA_ENV)
    if tar_sha is not None and (not isinstance(tar_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", tar_sha)):
        raise state.ChainError("%s must be a literal SHA-256" % TAR_SHA_ENV)
    if bundle_fresh(uri):
        return info
    code = task.get("code")
    if not code:
        raise state.ChainError("the code bundle expired and this task has no code clone")
    dirs = json.loads(info.get(DIRS_ENV) or "[]")
    if not isinstance(dirs, list) or not dirs or any(
        not isinstance(d, str) or not d or "\0" in d or Path(d).is_absolute() or ".." in Path(d).parts for d in dirs
    ):
        raise state.ChainError("%s must list clone-relative code directories" % DIRS_ENV)
    clone = registry.ensure_clone(task)
    if git_at(clone, "cat-file", "-e", commit + "^{commit}").returncode:
        if info[PUSHED_ENV] != "true" or push_remote(code) != info.get(REMOTE_ENV):
            raise state.ChainError("recorded commit is unavailable in the task clone or its configured source remote")
        tag = provenance_tag(task, stage["id"])
        legacy_tag = "refs/tags/nrp-run/%s/%s" % (task["name"], stage["id"])
        for ref in (commit, tag + "-" + commit, tag, legacy_tag):
            if (not git_at(clone, "fetch", "--no-tags", "--", info[REMOTE_ENV], ref).returncode
                    and not git_at(clone, "cat-file", "-e", commit + "^{commit}").returncode):
                break
        else:
            raise state.ChainError("could not fetch the recorded code commit from its source remote")
    with tempfile.TemporaryDirectory(prefix="nrp-restore-code-") as tmp:
        archive = Path(tmp) / "code.tgz"
        restored_sha, restored_tar_sha = pack(clone, commit, list(map(Path, dirs)), archive)
        if (tar_sha and restored_tar_sha != tar_sha) or (not tar_sha and restored_sha != sha):
            raise state.ChainError("the recorded commit did not reproduce the expired code bundle")
        restored_uri = uri.rsplit("/", 1)[0] + "/" + restored_sha + ".tgz"
        if restored_uri == uri or not bundle_fresh(restored_uri):
            upload_code_archive(archive, restored_uri)
        info.update({URI_ENV: restored_uri, SHA_ENV: restored_sha, TAR_SHA_ENV: restored_tar_sha})
        rewrite_env(container, info)
    state.task_txn(task["name"], lambda t: state.tev(t, "restored expired code bundle " + uri))
    return info


def record_bundle(task, job, info):
    task.setdefault("code_bundles", {})[job] = info


def code_container(doc, *, required=True):
    registry.manifest_structure(doc)
    pod = doc["spec"]["template"]["spec"]
    selected = [c for c in pod["containers"] + (pod.get("initContainers") or [])
                if any(e.get("name") == URI_ENV for e in c.get("env") or [])]
    if len(selected) == 1:
        return selected[0]
    if selected or required:
        raise state.ChainError("declare %s in exactly one Job container before reshipping" % URI_ENV)
    return None


def rewrite_env(container, values):
    env = [entry for entry in container.get("env") or [] if entry.get("name") not in ENV_NAMES]
    container["env"] = env + [{"name": name, "value": value} for name, value in values.items()]


def reship_code(task, job, manifest, *, allow_unpushed=False, additions=()):
    path = Path(manifest)
    try:
        doc = registry.manifest_doc(path)
        container = code_container(doc)
        info = publish(task, job, allow_unpushed=allow_unpushed, additions=additions)
        rewrite_env(container, info)
        with tempfile.TemporaryDirectory(prefix=".nrp-reship-", dir=path.parent) as tmp:
            updated = Path(tmp) / path.name
            registry.manifest_write(updated, doc)
            problems = registry.manifest_check(updated, task["namespace"], job)
            if problems:
                raise state.ChainError("; ".join(problems))
            updated.chmod(path.stat().st_mode & 0o777)
            updated.replace(path)
    except (state.ChainError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        sys.exit("reship refused: %s" % exc)
    uri = info[URI_ENV]
    def record(t):
        record_bundle(t, job, info)
        state.tev(t, "reshipped code for %s -> %s" % (job, uri))
    state.task_txn(task["name"], record)
    if info[PUSHED_ENV] == "false":
        print("DEBUG ONLY: this commit was not pushed.")
    print("reshipped: %s now points to %s. Resubmit with `nrp-task submit %s --reason ...`." % (job, uri, job))
    return 0


def ship_code(task, args):
    name = task["name"]
    if not re.fullmatch(r"%s-[a-z0-9-]{1,40}" % re.escape(name), args.name):
        sys.exit("ship NAME must be %s-<suffix> (lowercase)" % name)
    try:
        info = publish(task, args.name, args.from_dir, allow_unpushed=args.allow_unpushed, additions=args.add)
    except (state.ChainError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        sys.exit("ship refused: %s" % exc)
    uri = info[URI_ENV]
    def record(t):
        record_bundle(t, args.name, info)
        state.tev(t, "shipped code %s -> %s" % (args.name, uri))
    state.task_txn(name, record)
    print(uri)
    if info[PUSHED_ENV] == "false":
        print("DEBUG ONLY: this commit was not pushed.")
    print("Set these Job container env entries:")
    for key, value in info.items():
        print("- name: %s\n  value: %s" % (key, json.dumps(value)))
    print("Job startup prefix (shell, AWS CLI, sha256sum, tar, writable /work, and S3 read credentials):")
    print('code_dir=$(mktemp -d /work/nrp-code.XXXXXX) &&')
    print('aws --endpoint-url %s s3 cp "$NRP_CODE_URI" "$code_dir/code.tgz" &&' % shlex.quote(state.S3_JOB_ENDPOINT))
    print('printf \'%s  %s\\n\' "$NRP_CODE_SHA256" "$code_dir/code.tgz" | sha256sum -c - &&')
    print('tar -xzf "$code_dir/code.tgz" -C "$code_dir" &&')
    print('unlink "$code_dir/code.tgz" &&')
    print('cd "$code_dir" && exec YOUR_JOB_COMMAND')
    return 0


def cleanup_task_code(task, *, dry_run):
    """Preserve all submitted commits with remote tags before deleting task branches."""
    if task["status"] not in ("done", "failed", "cancelled"):
        raise state.ChainError("code cleanup requires a finished task")
    heads = task.get("code_remote_heads") or {}
    if not heads:
        print("No pushed task code branches to clean up.")
        return
    code = task["code"]
    cwd = code["clone"] if Path(code["clone"]).is_dir() else code["repo"]
    for remote, branches in sorted(heads.items()):
        tags = {}
        for stage in task["stages"]:
            history = [*(stage.get("submitted_code_history") or []),
                       stage.get("submitted_code") or {}, stage.get("done_code") or {}]
            tag = provenance_tag(task, stage["id"])
            for info in history:
                if info.get(PUSHED_ENV) != "true" or info.get(REMOTE_ENV) != remote:
                    continue
                commit = info[COMMIT_ENV]
                ref = tag
                existing = checked_git(cwd, "could not inspect provenance tag", "ls-remote", "--", remote, ref)
                previous = tags.get(ref) or (existing.split()[0] if existing else None)
                if previous and previous != commit:
                    ref = tag + "-" + commit
                tags[ref] = commit
        for ref, commit in sorted(tags.items()):
            print("Tag %s at %s on %s" % (ref, commit, remote))
        for ref, commit in sorted(branches.items()):
            print("Delete %s from %s if it still points to %s" % (ref, remote, commit))
        if dry_run:
            continue
        # Publish all tags first. A conflicting tag or failed push leaves the branch available.
        for ref, commit in sorted(tags.items()):
            if git_at(cwd, "cat-file", "-e", commit + "^{commit}").returncode:
                checked_git(cwd, "could not fetch submitted stage commit " + commit, "fetch", "--no-tags", "--", remote, commit)
            checked_git(cwd, "could not push provenance tag " + ref, "push", "--", remote, commit + ":" + ref)
        for ref, commit in sorted(branches.items()):
            current = checked_git(cwd, "could not read remote task branch", "ls-remote", "--", remote, ref)
            if not current:
                continue
            checked_git(cwd, "could not delete task branch (it may have moved): " + ref,
                        "push", "--force-with-lease=%s:%s" % (ref, commit), "--", remote, ":" + ref)
    if not dry_run:
        state.task_txn(task["name"], lambda t: state.tev(t, "published submitted code tags and cleaned remote task branches"))
