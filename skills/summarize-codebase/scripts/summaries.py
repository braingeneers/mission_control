"""Source-summary maintenance. Python 3.10+, stdlib only; never imports project code."""

import argparse
import ast
from collections import defaultdict
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import warnings

# Research scripts contain invalid escape sequences; parsing them should stay quiet.
warnings.filterwarnings("ignore", category=SyntaxWarning)

EXTENSIONS = {".py", ".js", ".html", ".css"}
BASE_SKIPPED_DIRS = {"__pycache__", "vendor", "vendored", "third_party", "generated", "build", "dist", "node_modules", "site-packages"}
TEST_DIRS = {"tests", "test", "internal_tests", "testing"}
DEFAULT_BRIEF_DIRS = {"figures", "figs", "plots", "scratch", "scratch2", "example_plots", "diagrams"}
SKIPPED_DIRS = set(BASE_SKIPPED_DIRS)
BRIEF_DIRS = set(DEFAULT_BRIEF_DIRS)
AREAS = {}
LIBRARY = LIBRARY_NOTE = None
IMPORT_REWRITES = {}
AREA_FALLBACK = "{top}"
REPO_ROOT = None
SPLIT_PACKAGES = True


def repo_root(explicit=None):
    if explicit is not None:
        return Path(explicit).resolve()
    return Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()


def configure(root):
    """Load optional repository configuration; reset defaults on every call."""
    global SKIPPED_DIRS, BRIEF_DIRS, AREAS, LIBRARY, LIBRARY_NOTE, IMPORT_REWRITES, AREA_FALLBACK, REPO_ROOT, SPLIT_PACKAGES
    path = root / ".code-summaries.json"
    cfg = json.loads(path.read_text()) if path.exists() else {}
    SKIPPED_DIRS = BASE_SKIPPED_DIRS | set(cfg.get("skipped_dirs", []))
    BRIEF_DIRS = set(cfg.get("brief_dirs", DEFAULT_BRIEF_DIRS))
    AREAS = cfg.get("areas", {})
    LIBRARY, LIBRARY_NOTE = cfg.get("library"), cfg.get("library_note")
    IMPORT_REWRITES = cfg.get("import_rewrites", {})
    AREA_FALLBACK = cfg.get("area_fallback", "{top}")
    SPLIT_PACKAGES = cfg.get("split_packages", True)
    REPO_ROOT = root


DEFAULT_FLOW = "Project scripts; see per-file summaries."


def feature_area(rel):
    for prefix in sorted(AREAS, key=len, reverse=True):
        if rel.startswith(prefix):
            return AREAS[prefix][0]
    top = rel.split("/")[0] if "/" in rel else "(repo root)"
    parts = rel.split("/")
    if SPLIT_PACKAGES and REPO_ROOT and len(parts) > 2 and (REPO_ROOT / top / "__init__.py").exists():
        packages = [p for p in (REPO_ROOT / top).iterdir() if p.is_dir() and (p / "__init__.py").exists()]
        if len(packages) > 1:
            top += "/" + parts[1]
    return AREA_FALLBACK.format(top=top)


def area_flows():
    flows = {}
    for name, flow in AREAS.values():
        flows.setdefault(name, flow)
    return flows


def tier(rel):
    parts = rel.split("/")[:-1]
    return "brief" if any(p in BRIEF_DIRS or p.endswith("_fig") for p in parts) else "full"


def digest(path):
    # Normalize checkout line endings so hashes survive Windows/Linux clones.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(root, *args):
    result = subprocess.run(
        [os.environ.get("CODE_SUMMARIES_GIT", "git"), "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8", errors="replace").strip()


def candidates(root):
    """Tracked plus untracked-unignored files; os.walk fallback without Git."""
    try:
        listed = [p for p in git(root, "ls-files", "-co", "--exclude-standard", "-z").split("\0") if p]
        return sorted(p for p in listed if (root / p).is_file())
    except (RuntimeError, OSError):
        found = []
        for directory, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            found += [(Path(directory) / n).relative_to(root).as_posix() for n in names]
        return sorted(found)


def discover(root, include_tests=False):
    skipped_dirs = set(SKIPPED_DIRS) | (set() if include_tests else TEST_DIRS)
    files, trivial, holes = {}, {}, {}
    for rel in candidates(root):
        parts = rel.split("/")
        if Path(rel).suffix not in EXTENSIONS or "/" not in rel:
            continue
        bad = next((i for i, p in enumerate(parts[:-1]) if p in skipped_dirs or p.startswith(".")), None)
        if bad is not None:
            holes["/".join(parts[:bad + 1]) + "/"] = "excluded directory"
            continue
        path, name = root / rel, parts[-1]
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            holes[rel] = "symlink/outside source root"
            continue
        if name.startswith("TODO_") or (not include_tests and (name.startswith("test_") or name.endswith("_test.py"))):
            holes[rel] = "test or placeholder"
            continue
        if name == "__init__.py":
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"))
                simple = all(isinstance(n, (ast.Import, ast.ImportFrom)) or
                             (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)) or
                             (isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
                              and isinstance(n.value, (ast.List, ast.Tuple))
                              and all(isinstance(v, ast.Constant) and isinstance(v.value, str) for v in n.value.elts))
                             for n in tree.body)
                if simple:
                    exports = [ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
                    trivial[rel] = "; ".join(exports) or "Package marker."
                    continue
            except SyntaxError:
                pass
        files[rel] = digest(path)
    return dict(sorted(files.items())), dict(sorted(trivial.items())), dict(sorted(holes.items()))


def module_name(path):
    return re.sub(r"\.(py|js|html|css)$", "", path).replace("/", ".").removesuffix(".__init__")


def symbols(info):
    names = {n.name for n in info.get("classes", []) + info.get("functions", [])}
    if info.get("tree"):
        for node in info["tree"].body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names.update(n.id for target in targets for n in ast.walk(target) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    return sorted(names)


class Resolver:
    """Resolve imports the way these scripts run: repo root, the script's directory, then its ancestors."""

    def __init__(self, root, known):
        self.root, self.known = root, set(known)

    def module_file(self, base, dotted):
        stem = (base + "/" if base else "") + dotted.replace(".", "/")
        for rel in (stem + ".py", stem + "/__init__.py"):
            if rel in self.known:
                return rel
        return None

    def resolve(self, rel, target):
        """Return (resolved_rel, symbol) for an intra-repo import, else None."""
        if target.split(".")[0] == LIBRARY:
            return None
        parent = str(Path(rel).parent).replace("\\", "/")
        bases = [""]
        while parent not in ("", "."):
            bases.append(parent)
            parent = str(Path(parent).parent).replace("\\", "/")
        pieces = target.split(".")
        if pieces[0] in IMPORT_REWRITES and len(pieces) > 1:
            replacement = IMPORT_REWRITES[pieces[0]]
            pieces = ([replacement] if replacement else []) + pieces[1:]
            bases = [""]
        for base in bases:
            # Longest module prefix first; the remainder (at most one name) is the imported symbol.
            for cut in (len(pieces), len(pieces) - 1):
                if cut < 1:
                    continue
                found = self.module_file(base, ".".join(pieces[:cut]))
                if found:
                    return found, ".".join(pieces[cut:])
        return None


def facts(root, rel, resolver=None):
    source = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
    result = {"classes": [], "functions": [], "imports": [], "local": [], "tree": None, "entry": False}
    if not rel.endswith(".py"):
        return result
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        result["parse_error"] = f"SyntaxError at line {exc.lineno}: {exc.msg}"
        return result
    result["tree"] = tree
    result["entry"] = any(isinstance(n, ast.If) and "__name__" in ast.unparse(n.test) and "__main__" in ast.unparse(n.test) for n in tree.body) or rel.endswith("/__main__.py")
    result["classes"] = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    result["functions"] = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    result["entry"] = result["entry"] or any(n.name == "main" for n in result["functions"])
    # Research scripts often run top-level code without a main guard.
    result["entry"] = result["entry"] or any(
        isinstance(child, ast.Call)
        for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom, ast.Assign))
        for child in ast.walk(node)
    )
    package = module_name(rel).split(".") if rel.endswith("/__init__.py") else module_name(rel).split(".")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append((alias.name, alias.asname or alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            prefix = ".".join(package[:len(package) - node.level + 1]) if node.level else ""
            mod = ".".join(x for x in (prefix, node.module) if x)
            for alias in node.names:
                result["imports"].append((f"{mod}.{alias.name}", alias.asname or alias.name, node.lineno))
    if resolver:
        for target, alias, line in result["imports"]:
            hit = resolver.resolve(rel, target)
            if hit:
                qualified = module_name(hit[0]) + ("." + hit[1] if hit[1] else "")
                result["local"].append((qualified, alias, line))
    return result


def compact(value, limit=240):
    text = " ".join(str(value).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def signature(node):
    value = f"{node.name}({ast.unparse(node.args)})"
    if node.returns:
        value += " -> " + ast.unparse(node.returns)
    return value


def purpose(node, annotations, name):
    if name in annotations.get("purposes", {}):
        return compact(annotations["purposes"][name], 450)
    doc = ast.get_docstring(node)
    return compact(doc.split("\n\n")[0], 450) if doc else "unclear — see source"


def effects(node):
    found = set()
    for child in ast.walk(node):
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            if any(ast.unparse(t).startswith("self.") for t in targets):
                found.add("mutates instance state")
        if isinstance(child, ast.Call):
            name = ast.unparse(child.func)
            if name.split(".")[-1] in {"save", "dump", "to_csv", "savefig", "write", "write_text", "write_bytes", "to_parquet", "savez", "savez_compressed"}:
                found.add("write call (static hint)")
    return "; ".join(sorted(found)) or "unclear — see source"


def render(root, rel, annotation, info, consumers, callers):
    level = tier(rel)
    lines = [f"# {Path(rel).name}", "", f"**Path:** `{rel}`", f"**Module:** `{module_name(rel)}`",
             f"**Feature Area:** `{feature_area(rel)}`", f"**Tier:** `{level}`",
             f"**Entry point:** {'yes — main / script execution (static candidate)' if info['entry'] else 'no — library or imported component'}",
             "", "## Overview", annotation["overview"], "", "## Connections"]
    for target in sorted(set(t for t, _, _ in info["local"])):
        mod, _, symbol = target.rpartition(".")
        lines.append(f"- **Uses:** `{symbol}` from `{mod}` — imports (static evidence).")
    library = sorted(set(t for t, _, _ in info["imports"] if t.split(".")[0] == LIBRARY))
    if library:
        lines.append(f"- **Library:** {', '.join(f'`{t}`' for t in library[:25])}{' …' if len(library) > 25 else ''} — {LIBRARY_NOTE}.")
    for caller in sorted(consumers.get(module_name(rel), [])):
        lines.append(f"- **Used by:** `{caller}` — import consumer hint; not a proven runtime call.")
    lines += [f"- **Shared data:** {item}" for item in annotation.get("connections", [])]
    if lines[-1] == "## Connections":
        lines.append("None")
    lines += ["", "## Dependencies"]
    resolved_aliases = {alias for _, alias, _ in info["local"]}
    dependencies = sorted(set(t for t, a, _ in info["imports"] if t.split(".")[0] not in sys.stdlib_module_names
                              and t.split(".")[0] != LIBRARY and a not in resolved_aliases))
    lines += [f"- `{target}` — external or unresolved local import; source import evidence." for target in dependencies] or ["None"]
    lines += ["", "## Classes"]
    if not info["classes"]:
        lines.append("None")
    for cls in info["classes"]:
        bases = ", ".join(ast.unparse(b) for b in cls.bases)
        lines += [f"### {cls.name}({bases})", f"> {purpose(cls, annotation, cls.name)}",
                  f"**Source:** `{rel}:{cls.lineno}`", "**Kind:** class. **Instantiated by:** " + ("; ".join(sorted(callers.get(module_name(rel) + '.' + cls.name, []))) or "unclear — see source")]
        methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        init = next((n for n in methods if n.name == "__init__"), None)
        lines.append(f"**Constructor:** `{signature(init)}`" if init else "**Constructor:** inherited / implicit")
        attrs = {}
        for method in methods:
            for node in ast.walk(method):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                            attrs.setdefault(target.attr, (ast.unparse(node.annotation) if isinstance(node, ast.AnnAssign) else "inferred at runtime", compact(ast.unparse(node.value), 130) if node.value else "annotation only"))
        lines.append("**Key attributes:**")
        if attrs and level == "full":
            lines += ["| Name | Type | Assignment / meaning |", "| --- | --- | --- |"]
            lines += [f"| `{name}` | {kind} | `{value}` |" for name, (kind, value) in sorted(attrs.items())]
        else:
            lines.append(", ".join(f"`{name}`" for name in sorted(attrs)) or "None")
        lines.append("**Methods:**")
        for method in methods:
            if method.name == "__init__":
                continue
            lines += [f"#### `{signature(method)}`", f"> {purpose(method, annotation, cls.name + '.' + method.name)}",
                      f"> **Called by:** unresolved static dispatch. **Side effects:** {effects(method)}.",
                      f"**Source:** `{rel}:{method.lineno}`"]
        if not any(n.name != "__init__" for n in methods):
            lines.append("None")
    lines += ["", "## Functions"]
    for node in info["functions"]:
        lines += [f"### `{signature(node)}`", f"> {purpose(node, annotation, node.name)}",
                  f"> **Called by:** {'; '.join(sorted(callers.get(module_name(rel) + '.' + node.name, []))) or 'unclear — see source'}. **Side effects:** {effects(node)}.",
                  f"**Source:** `{rel}:{node.lineno}`"]
    for symbol in annotation.get("symbols", []):
        lines += [f"### `{symbol.get('signature', symbol['name'])}`", f"> {symbol['purpose']}", f"**Source:** `{rel}:{symbol['line']}`"]
    if not info["functions"] and not annotation.get("symbols"):
        lines.append("None")
    for title, key in (("Config / CLI", "config"), ("Data Shapes", "data_shapes"), ("Notes", "notes")):
        lines += ["", f"## {title}"]
        values = list(annotation.get(key, []))
        if key == "notes" and info.get("parse_error"):
            values.append(info["parse_error"])
        if key == "config" and values:
            lines += ["| Configuration / CLI and meaning |", "| --- |"]
            lines += ["| " + item.replace("|", "\\|").replace("\n", " ") + " |" for item in values]
        else:
            lines += [f"- {item}" for item in values] or ["None"]
    return "\n".join(lines) + "\n"


def read_summary(path):
    text = path.read_text(encoding="utf-8")
    def field(name, default=None):
        match = re.search(r"^\*\*" + re.escape(name) + r":\*\* `?([^`\n]+)", text, re.M)
        if not match:
            if default is not None:
                return default
            raise ValueError(f"Missing {name}: {path}")
        return match.group(1)
    overview = re.search(r"^## Overview\n(.+?)(?=\n## |\Z)", text, re.M | re.S)
    return {"file": field("Path"), "module": field("Module"), "feature_area": field("Feature Area"),
            "tier": field("Tier", "full"), "entry": field("Entry point").startswith("yes"),
            "overview": compact(overview.group(1) if overview else "unclear — see source", 300),
            "uses": re.findall(r"^- \*\*Uses:\*\* `([^`]+)` from `([^`]+)`", text, re.M),
            "symbols": re.findall(r"^### `?([\w]+)\(", text, re.M)}


def summary_files(out):
    # Per-file summaries live in mirrored subdirectories; top-level files are the indexes.
    return sorted(p for p in out.rglob("*.md") if p.parent != out)


def refresh_reverse(out, consumers, callers):
    """Refresh derived incoming edges without re-reviewing unchanged semantics."""
    for path in summary_files(out):
        record = read_summary(path)
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^- \*\*Used by:\*\*.*\n", "", text, flags=re.M)
        incoming = [f"- **Used by:** `{caller}` — import consumer hint; not a proven runtime call."
                    for caller in sorted(consumers.get(record["module"], []))]
        if incoming:
            text = text.replace("## Connections\nNone\n", "## Connections\n")
            text = text.replace("## Connections\n", "## Connections\n" + "\n".join(incoming) + "\n", 1)
        section, current = None, None
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("## "):
                section, current = line[3:], None
            match = re.match(r"^### `?(\w+)\(", line)
            if match:
                current = match.group(1)
            if line.startswith("#### "):
                current = None
            hints = "; ".join(sorted(callers.get(record["module"] + "." + str(current), []))) or "unclear — see source"
            if section == "Classes" and current and line.startswith("**Kind:** class. **Instantiated by:**"):
                lines[index] = "**Kind:** class. **Instantiated by:** " + hints
            if section == "Functions" and current and line.startswith("> **Called by:**"):
                lines[index] = re.sub(r"^> \*\*Called by:\*\* .*?\. \*\*Side effects:\*\*", "> **Called by:** " + hints + ". **Side effects:**", line)
        updated = "\n".join(lines) + "\n"
        if updated != path.read_text(encoding="utf-8"):
            path.write_text(updated, encoding="utf-8")


def load_status(out):
    """Hand-curated ``_STATUS.json`` (kept across rebuilds): which code is current, legacy or removed,
    what replaces it, and per feature area the real entry points and where outputs go."""
    path = out / "_STATUS.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    files, areas = data.get("files", {}), data.get("areas", {})

    def tag(rel):
        hits = [k for k in files if rel == k or (k.endswith("/") and rel.startswith(k))]
        if not hits:
            return ""
        entry = files[max(hits, key=len)]
        prefer = f" → `{entry['prefer']}`" if entry.get("prefer") else ""
        return f"**[{entry['status']}{prefer}]** "
    return tag, areas


def assemble(root, out, meta, trivial, holes, features):
    records = [read_summary(path) for path in summary_files(out)]
    tag, area_status = load_status(out)
    for record in records:
        record["symbols"] = sorted(set(record["symbols"]) | set(meta["files"].get(record["file"], {}).get("symbols", [])))
    heading = f"Generated: {meta['generated']} | commit: {meta['commit'] or 'unavailable'} | mode: {meta['mode']}"
    brief = sum(r["tier"] == "brief" for r in records)
    index = ["# Code summaries", "", heading,
             f"\n{len(records)} file summaries ({len(records) - brief} full, {brief} brief); {len(trivial)} package markers. Scope: all project directories except known holes.",
             "", "Use `_FEATURES.md` for behavior, `_GRAPH.md` for import consumers. Check freshness with the helper before relying on summaries.",
             "`brief` summaries (figure/scratch scripts) have a reviewed overview plus AST facts only; read source for details.",
             "", "## Directory tree", "```text"]
    dirs = sorted({str(Path(r["file"]).parent).replace("\\", "/") for r in records})
    index += ["  " * (d.count("/")) + d.rsplit("/", 1)[-1] + "/" for d in sorted(set(p.as_posix() for d in dirs for p in [Path(d), *Path(d).parents] if p.as_posix() != "."))]
    index += ["```"]
    grouped = defaultdict(list)
    for record in records:
        grouped[record["feature_area"]].append(record)
    for directory in dirs:
        index += ["", f"## {directory}"]
        for r in records:
            if str(Path(r["file"]).parent).replace("\\", "/") != directory:
                continue
            syms = r["symbols"] if len(r["symbols"]) <= 20 else r["symbols"][:20] + [f"… (+{len(r['symbols']) - 20})"]
            index.append(f"- {tag(r['file'])}[{Path(r['file']).name}]({r['file']}.md) — {r['overview']} Symbols: {', '.join(syms) or 'module-level code'}.")
    index += ["", "## Package markers and re-exports (no per-file summary)"]
    index += [f"- `{path}` — {compact(exports, 600)}" for path, exports in trivial.items()]
    index += ["", "## Known holes",
              f"- Skipped directory names anywhere in the tree: {', '.join(f'`{d}`' for d in sorted(SKIPPED_DIRS | TEST_DIRS))}; dot-directories; repo-root files.",
              "- Notebooks, data, weights, images, shell/SLURM/YAML files, and other non-source assets are not summarized.",
              *([f"- `{LIBRARY}`: {LIBRARY_NOTE or 'external library'}."] if LIBRARY else [])]
    index += [f"- `{path}` — {reason}." for path, reason in holes.items()]
    if meta.get("stale_files"):
        index += ["", "## Missing or stale summaries"]
        index += [f"- `{path}` — refresh before relying on navigation." for path in meta["stale_files"]]
    graph = ["# Connections graph", "", heading, "", "Edges below are source-backed **imports** resolved against the repo root and the importing script's directory (sys.path style), not runtime calls. Dynamic dispatch, `sys.path` hacks to unusual locations, wildcard imports and re-exports can be incomplete. Configured external library imports appear under `**Library:**` in summaries."]
    feature_index = ["# Features", "", heading]
    ordered = list(features) + sorted(a for a in grouped if a not in features)
    for number, area in enumerate(ordered, 1):
        members = grouped.get(area, [])
        if not members:
            continue
        flow = features.get(area, DEFAULT_FLOW)
        entry = [r for r in members if r["entry"] and r["tier"] == "full"]
        graph += ["", f"## {area}", flow]
        for r in members:
            for symbol, mod in r["uses"]:
                graph.append(f"- `{r['module']}` --imports--> `{mod}.{symbol}`")
        full = [r for r in members if r["tier"] == "full"]
        short = [r for r in members if r["tier"] == "brief"]
        extra = area_status.get(area, {})
        entry_text = ", ".join(f"`{m}`" for m in extra["entry"]) if extra.get("entry") else \
            (", ".join(f"[{r['module']}]({r['file']}.md)" for r in entry[:60]) or "library-style components below") + (" …" if len(entry) > 60 else "")
        feature_index += ["", f"## {number}. {area}", flow, "", "**Entry points (full tier):** " + entry_text]
        if extra.get("outputs"):
            feature_index += ["", "**Outputs:** " + extra["outputs"]]
        feature_index += ["", "**Supporting files:**"]
        feature_index += [f"- {tag(r['file'])}[{Path(r['file']).name}]({r['file']}.md) — {r['overview']}" for r in full] or ["None"]
        if short:
            feature_index += ["", "**Figure / scratch scripts (brief):**"]
            feature_index += [f"- {tag(r['file'])}[{r['file']}]({r['file']}.md) — {compact(r['overview'], 160)}" for r in short]
    # Running backlog: what still needs (re)annotation, grouped so people can pick a folder.
    stale = meta.get("stale_files", [])
    todo = ["# Summary backlog", "", heading, "",
            f"{len(stale)} source files have missing or stale summaries. Clear a folder with",
            "`.agents/skills/summarize-codebase/scripts/refresh.sh '<folder>'`, or everything with `refresh.sh`.",
            "This list is rewritten on every build; `summaries.py check` shows the live state between builds."]
    folders = defaultdict(list)
    for path in stale:
        parts = path.split("/")
        folders["/".join(parts[:2]) if len(parts) > 2 else parts[0]].append(path)
    if folders:
        todo += ["", "| Folder | Stale files | Full | Brief |", "| --- | --- | --- | --- |"]
        for folder, paths in sorted(folders.items(), key=lambda item: (-len(item[1]), item[0])):
            full = sum(tier(p) == "full" for p in paths)
            todo.append(f"| `{folder}/` | {len(paths)} | {full} | {len(paths) - full} |")
        todo += ["", "## Files"]
        for folder, paths in sorted(folders.items()):
            todo += ["", f"### {folder}/"] + [f"- `{p}` ({tier(p)})" for p in paths]
    else:
        todo += ["", "Nothing pending."]
    for name, lines in (("_INDEX.md", index), ("_FEATURES.md", feature_index), ("_GRAPH.md", graph), ("_TODO.md", todo)):
        (out / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "build", "check"])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--all", action="store_true")
    modes.add_argument("--since")
    parser.add_argument("paths", nargs="*", help="Repo-relative source paths/globs; quote wildcards")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--annotations", type=Path, nargs="+", default=[])
    parser.add_argument("--allow-partial", action="store_true",
                        help="build: summarize only selected files that have annotations; leave the rest stale")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_intermixed_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ required")
    if args.paths and (args.all or args.since):
        parser.error("paths cannot be combined with --all or --since")
    root = repo_root(args.root)
    configure(root)
    out = root / ".code-summaries"
    features = area_flows()
    meta_path = out / "_META.json"
    old = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    files, trivial, holes = discover(root, args.include_tests)
    resolver = Resolver(root, list(files) + list(trivial))
    previous = old.get("files", {})
    trivial_hashes = {p: digest(root / p) for p in trivial}
    index_changed = old.get("trivial_files", {}) != trivial_hashes
    stale = {p for p, sha in files.items() if previous.get(p, {}).get("sha256") != sha or not (out / (p + ".md")).exists()}
    deleted = {p for p in previous if p not in files}
    since = args.since or old.get("commit")
    head, warning = None, None
    try:
        head = git(root, "rev-parse", "HEAD")
        if not since:
            since = git(root, "log", "-1", "--format=%H", "--", ".code-summaries") or None
    except (RuntimeError, OSError) as exc:
        if args.since:
            parser.error(str(exc))
        warning = str(exc)
    mode = "path" if args.paths else "all" if args.all or (not since and not old) else "since" if args.since else "incremental"
    selected = set(files) if mode == "all" else set(stale)
    if args.since:
        # --no-renames includes both old and new names; NUL output handles spaces.
        try:
            changed = git(root, "diff", "--name-only", "--no-renames", "-z", args.since).split("\0")
            selected |= set(changed) & set(files)
        except (RuntimeError, OSError) as exc:
            parser.error(str(exc))
    if mode == "path":
        patterns = [p.replace("\\", "/").removeprefix("./").rstrip("/") for p in args.paths]
        match = lambda p: any(p == pattern or p.startswith(pattern + "/") or fnmatch.fnmatchcase(p, pattern) for pattern in patterns)
        selected = {p for p in files if match(p)}
        deleted = {p for p in deleted if match(p)}
        if not selected and not deleted and not any(match(p) for p in trivial):
            parser.error("no supported in-scope files match those paths")
    # Public symbol removal invalidates consumers, even in a targeted refresh.
    all_facts = {}
    if args.action != "check":
        for rel in sorted(selected):
            all_facts[rel] = facts(root, rel, resolver)
        removed_targets = set()
        for rel in selected | deleted:
            current = all_facts.get(rel, {})
            names = set(symbols(current))
            removed_names = {name for name in previous.get(rel, {}).get("symbols", []) if not name.startswith("_") and name not in names}
            removed_targets |= {module_name(rel) + "." + name for name in removed_names}
            if removed_names:
                removed_targets.add(module_name(rel))
            if rel in deleted:
                removed_targets.add(module_name(rel))
        for rel, record in previous.items():
            if rel in files and any(target == removed or target.startswith(removed + ".") or removed.startswith(target + ".") for target in record.get("uses", []) for removed in removed_targets):
                selected.add(rel)
                all_facts.setdefault(rel, facts(root, rel, resolver))
    if args.action == "check":
        selected = stale
        deleted = set(previous) - set(files)
    report = {"mode": mode, "since": since, "commit": head, "count": len(selected),
              "tiers": {"full": sum(tier(p) == "full" for p in selected), "brief": sum(tier(p) == "brief" for p in selected)},
              "files": sorted(selected), "feature_areas": {p: feature_area(p) for p in sorted(selected)}, "deleted": sorted(deleted), "index_changed": index_changed, "warning": warning}
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.action != "build":
        print(f"{mode}; since {since or 'none'}; {len(selected)} files ({report['tiers']['full']} full, {report['tiers']['brief']} brief); {len(deleted)} removed")
        for rel in sorted(selected):
            print(f"{rel}\t{tier(rel)}")
        for rel in sorted(deleted):
            print("DELETE " + rel)
        if warning:
            print("Git unavailable; content hashes remain authoritative: " + warning, file=sys.stderr)
    if args.action == "check":
        return 1 if selected or deleted or index_changed or not all((out / name).exists() for name in ("_INDEX.md", "_FEATURES.md", "_GRAPH.md", "_META.json")) else 0
    if args.action == "plan":
        return 0
    annotations = {}
    for path in args.annotations:
        annotations.update(json.loads(path.read_text(encoding="utf-8")))
    if args.allow_partial:
        skipped = sorted(p for p in selected if p not in annotations)
        selected = {p for p in selected if p in annotations}
        if skipped:
            print(f"partial build: {len(skipped)} selected files lack annotations and stay stale", file=sys.stderr)
    # Validate the entire batch before writing any output.
    errors = []
    for rel in sorted(selected):
        annotation = annotations.get(rel)
        if not annotation:
            errors.append(f"missing reviewed annotation: {rel}")
            continue
        # Accept raw-byte hashes from reviewers; persisted hashes are LF-normalized.
        if annotation.get("source_sha256") not in {files[rel], hashlib.sha256((root / rel).read_bytes()).hexdigest()}:
            errors.append(f"annotation source hash is stale: {rel}")
        if not isinstance(annotation.get("overview"), str) or not annotation["overview"].strip():
            errors.append(f"missing overview: {rel}")
        for key in ("config", "data_shapes", "notes", "connections"):
            if tier(rel) == "brief":
                annotation.setdefault(key, [])
            if not isinstance(annotation.get(key), list):
                errors.append(f"annotation requires {key} list: {rel}")
        if not isinstance(annotation.get("purposes", {}), dict):
            errors.append(f"purposes must be an object: {rel}")
    if errors:
        parser.error("; ".join(errors[:30]) + (f" (+{len(errors) - 30} more)" if len(errors) > 30 else "") + "; follow summarize-codebase/SKILL.md")
    # Scan imports for conservative file-level consumer hints. No runtime imports.
    consumers = defaultdict(set)
    callers = defaultdict(set)
    if selected or deleted:
        for rel in files:
            if rel not in all_facts:
                all_facts[rel] = facts(root, rel, resolver)
            info = all_facts[rel]
            for target, _, _ in info["local"]:
                for candidate in (target, target.rpartition(".")[0]):
                    consumers[candidate].add(module_name(rel))
            # Only direct calls to named local/imported functions/classes are hints.
            # Attribute receiver dispatch remains unresolved; never guess its type.
            bindings = {alias: target for target, alias, _ in info["local"]}
            bindings.update({n.name: module_name(rel) + "." + n.name for n in info["functions"] + info["classes"]})
            if info["tree"]:
                for node in ast.walk(info["tree"]):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in bindings:
                        callers[bindings[node.func.id]].add(f"{rel}:{node.lineno} (named-call hint)")
        # Cap noisy hint lists so shared helpers stay readable.
        for table in (consumers, callers):
            for key, value in table.items():
                if len(value) > 40:
                    table[key] = set(sorted(value)[:40]) | {f"… {len(value) - 40} more (grep _GRAPH.md)"}
    refreshed = dict(previous)
    out.mkdir(parents=True, exist_ok=True)
    for rel in sorted(deleted):
        target = (out / (rel + ".md")).resolve()
        if not target.is_relative_to(out.resolve()) or target.parent == out.resolve():
            parser.error(f"unsafe metadata path: {rel}")
        target.unlink(missing_ok=True)
        refreshed.pop(rel, None)
    for rel in sorted(selected):
        info = all_facts[rel]
        target = out / (rel + ".md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(root, rel, annotations[rel], info, consumers, callers), encoding="utf-8")
        refreshed[rel] = {"sha256": files[rel], "tier": tier(rel), "symbols": symbols(info),
                          "uses": sorted(set(t for t, _, _ in info["local"]))}
    meta = {"commit": head, "generated": datetime.now(timezone.utc).date().isoformat(),
            "mode": mode, "files_refreshed": len(selected), "source_roots": ["<all project directories>"],
            "hash_normalization": "CRLF to LF", "files": dict(sorted(refreshed.items())),
            "stale_files": sorted(p for p in files if refreshed.get(p, {}).get("sha256") != files[p] or not (out / (p + ".md")).exists()),
            "include_tests": args.include_tests, "trivial_files": trivial_hashes}
    if selected or deleted:
        refresh_reverse(out, consumers, callers)
    assemble(root, out, meta, trivial, holes, features)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"{'up to date' if not selected and not deleted else 'refreshed'} (since {since or 'none'}); {len(refreshed)} summaries; {len(meta['stale_files'])} stale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
