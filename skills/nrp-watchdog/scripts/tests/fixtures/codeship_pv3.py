# Vendored test fixture, unmodified: braindance_proj predictor_v3/utils/jobs/codeship.py as of commit 0ef76058.
# nrp-task reship is tested against the real packer so the tarball layout (predictor_v3/ + extra package dirs) is the real one.
"""Agents: load the `nrp-cluster` skill (~/.claude/skills/nrp-cluster/SKILL.md + references) before submitting jobs or changing this file; policy here mirrors it (see docs/tooling/build/E_nrp_audit.md).

``--ship-code``: run a job on the pinned image with the code from your checkout, without an
image rebuild.

The image (``jobs/image.lock``) provides the stack: Python, torch, the Mamba kernels, BrainDance.
With ``--ship-code`` the submitter packs this checkout's ``predictor_v3/`` (git-tracked files
plus untracked, not-ignored ones, so a new ``experiments/<x>/`` folder is included; source and
config suffixes only) into a deterministic tarball, uploads it once to
``<s3_root>/code/<sha256[:16]>.tgz`` (content addressed: the same code is never uploaded
twice) and puts ``{"uri", "sha256"}`` in the spec as ``code``. The job name hashes the spec, so
different code gives a different job name.

In the pod, ``jobs.entry`` sees ``code``, downloads and verifies the tarball, unpacks it under
the pod's data volume, and re-executes itself with that directory first on ``PYTHONPATH``; the
whole job then runs the shipped code. Rebuild the image only when the stack (requirements,
BrainDance) or ``jobs/entry.py``'s bootstrap itself changes.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

PKG = "predictor_v3"
PKG_DIR = Path(__file__).resolve().parents[2]  # .../predictor_v3
SUFFIXES = frozenset({".py", ".yaml", ".yml", ".json", ".lock", ".txt", ".csv", ".ini"})
MAX_FILE_BYTES = 2 * 2**20  # a bigger file is data, not code: keep it on S3
MAX_TOTAL_BYTES = 40 * 2**20
ENV_EXTRA_PACKAGES = "PV3_CODE_EXTRA_PACKAGES"  # os.pathsep-separated package directories; opt-in
ENV_SHA = "PV3_CODE_SHA256"  # set in the re-executed process: the shipped code is active


class CodeShipError(RuntimeError):
    pass


@dataclass(frozen=True)
class Bundle:
    data: bytes
    sha256: str
    n_files: int
    git_head: str | None
    dirty: bool
    skipped: tuple[str, ...]  # files left out for size

    def describe(self) -> str:
        head = (self.git_head or "no git")[:10] + (" + uncommitted changes" if self.dirty else "")
        s = f"{self.n_files} files, {len(self.data) / 1024:.0f} KiB, sha256 {self.sha256[:16]}, git {head}"
        return s + (f"; left out (> {MAX_FILE_BYTES >> 20} MiB): {', '.join(self.skipped)}" if self.skipped else "")


def _git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise CodeShipError(f"--ship-code needs a git checkout of {PKG} ({e})") from e


def list_files(pkg_dir: Path = PKG_DIR) -> list[str]:
    """Paths relative to the repo root (``predictor_v3/...``): tracked + untracked-not-ignored."""
    repo = Path(_git(["rev-parse", "--show-toplevel"], pkg_dir).strip())
    rel = pkg_dir.resolve().relative_to(repo.resolve())
    out = _git(["ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", str(rel)], repo)
    names = sorted({n for n in out.split("\0") if n})
    base = pkg_dir.parent.resolve()
    return [str((repo / n).resolve().relative_to(base)) for n in names
            if Path(n).suffix in SUFFIXES and (repo / n).is_file()]


def build(pkg_dir: Path = PKG_DIR, *, extra_pkg_dirs: tuple[Path, ...] | None = None) -> Bundle:
    """Deterministic checkout bundle, optionally including sibling packages.

    Set PV3_CODE_EXTRA_PACKAGES to package directories separated by os.pathsep,
    e.g. /path/Avian_proj/finch_analysis. With --ship-code this permits
    job gate --module finch_analysis.<module>. Dependencies outside that package
    (e.g. figures and figstyle) must also be selected or already in the image.
    No env/argument means the original predictor_v3-only bundle, byte for byte.
    Extra packages use the same Git selection, suffix and size limits, and are
    unpacked beside predictor_v3 so existing pod PYTHONPATH bootstrap finds them.
    """
    # Read at build time so CLI --ship-code needs no new flags. Explicit () disables env.
    if extra_pkg_dirs is None:
        extra_pkg_dirs = tuple(Path(p).expanduser() for p in os.environ.get(ENV_EXTRA_PACKAGES, "").split(os.pathsep) if p)
    packages = [pkg_dir]
    seen = {PKG}
    for extra in sorted((Path(p).resolve() for p in extra_pkg_dirs), key=str):
        if not extra.is_dir() or not extra.name.isidentifier() or extra.name in seen:
            raise CodeShipError(f"invalid or duplicate extra package directory: {extra}")
        seen.add(extra.name)
        packages.append(extra)
    names, skipped, sources, extra_info = [], [], {}, {}
    for package in packages:
        root = package.parent
        package_names = []
        try:
            package_files = list_files(package)
        except ValueError as e:
            raise CodeShipError(f"package file escapes package root: {package}") from e
        for n in package_files:
            source = root / n
            # Extra code may not escape its package through symlinks.
            if package != pkg_dir and not source.resolve().is_relative_to(package):
                raise CodeShipError(f"extra package file escapes package: {source}")
            (skipped if source.stat().st_size > MAX_FILE_BYTES else package_names).append(n)
            sources[n] = source
        names.extend(package_names)
        if package != pkg_dir:
            extra_info[package.name] = {
                "git_head": _git(["rev-parse", "HEAD"], package).strip() or None,
                "dirty": bool(_git(["status", "--porcelain", "--", "."], package).strip()),
                "n_files": len(package_names),
            }
    head = _git(["rev-parse", "HEAD"], pkg_dir).strip() or None
    dirty = bool(_git(["status", "--porcelain", "--", "."], pkg_dir).strip())
    metadata = {"git_head": head, "dirty": dirty, "n_files": len(names)}
    if extra_info:
        metadata["extra_packages"] = extra_info
    info = json.dumps(metadata, sort_keys=True).encode()
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        def add(name: str, data: bytes) -> None:
            ti = tarfile.TarInfo(name)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(data))

        for n in names:
            add(n, sources[n].read_bytes())
        add(f"{PKG}/CODE_INFO.json", info)
    data = raw.getvalue()
    if len(data) > MAX_TOTAL_BYTES:
        raise CodeShipError(f"code tarball is {len(data) >> 20} MiB > {MAX_TOTAL_BYTES >> 20} MiB: is data checked in?")
    return Bundle(data, hashlib.sha256(data).hexdigest(), len(names), head, dirty, tuple(skipped))


def uri_for(s3_root: str, sha256: str) -> str:
    return f"{s3_root.rstrip('/')}/code/{sha256[:16]}.tgz"


def upload(s3, uri: str, bundle: Bundle) -> bool:
    """Upload unless already there (content addressed). Returns True if it uploaded."""
    if s3.exists(uri):
        return False
    s3.put_bytes(uri, bundle.data)
    return True


def install(s3, code: Mapping[str, str], workdir: str) -> str:
    """Pod side: download, verify and unpack the tarball; returns the directory to put on PYTHONPATH."""
    data = s3.get_bytes(code["uri"])
    got = hashlib.sha256(data).hexdigest()
    if got != code["sha256"]:
        raise CodeShipError(f"{code['uri']}: sha256 {got} != spec {code['sha256']}")
    dest = os.path.join(workdir, "code", code["sha256"][:16])
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile() or m.name.startswith("/") or ".." in Path(m.name).parts:
                raise CodeShipError(f"unexpected tar member {m.name!r}")
        tar.extractall(dest)  # noqa: S202 - members checked above, sha256 verified
    return dest


def reexec(code: Mapping[str, str], s3, argv: list[str], env: Mapping[str, str], workdir: str,
           execve: Callable[..., None] = os.execve, chdir: Callable[[str], None] = os.chdir) -> None:
    """Install the shipped code and replace this process with ``python -m <entry> argv`` running it.

    ``python -m`` puts the working directory first on ``sys.path``, and the image's WORKDIR ``/app``
    holds the baked-in ``predictor_v3``; so the new process starts in the unpacked directory, or the
    image's code would shadow the shipped code."""
    dest = install(s3, code, workdir)
    chdir(dest)
    new_env = dict(env)
    new_env["PYTHONPATH"] = dest + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    new_env[ENV_SHA] = code["sha256"]
    print(f"ship-code: running {code['uri']} (sha256 {code['sha256'][:16]}) from {dest}", flush=True)
    execve(sys.executable, [sys.executable, "-m", "predictor_v3.utils.jobs.entry", *argv], new_env)
