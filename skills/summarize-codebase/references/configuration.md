# Optional repository configuration

Place a JSON object at repository-root `.code-summaries.json`. Omitted keys use defaults.

```json
{
  "areas": {"src/jobs/": ["Jobs", "Input records → jobs → result tables."]},
  "brief_dirs": ["figures", "plots", "scratch"],
  "skipped_dirs": ["archive", "outputs"],
  "library": "external_sdk",
  "library_note": "See the SDK's own documentation.",
  "import_rewrites": {"old_package": ""},
  "area_fallback": "{top}"
}
```

- `areas`: path-prefix → `[display_name, flow_description]`; longest prefix wins.
  Use a trailing slash to match a directory rather than names sharing its prefix.
- `brief_dirs`: replaces default directory-name set (figures, figs, plots, scratch,
  scratch2, example_plots, diagrams). Any directory ending `_fig` is always brief.
- `skipped_dirs`: extra directory names, anywhere in the path. Defaults exclude caches,
  vendor/vendored/third_party, generated, build/dist, node_modules, site-packages.
- `library`: optional top-level external import name, excluded from local resolution.
- `library_note`: optional navigation note rendered for those imports.
- `import_rewrites`: top-level legacy import prefix → replacement prefix; an empty
  replacement removes it. Rewritten imports resolve from the repository root.
- `split_packages`: boolean (default true); set false to keep fallback areas at
  top-level directories even for Python packages with multiple subpackages.
- `area_fallback`: format string with `{top}`; defaults to the top-level directory
  (or `top/subpackage` for a Python package with multiple child packages).
- Unknown keys are ignored; `_comment` may label examples.

Scope: .py/.js/.html/.css below repository subdirectories, tracked or untracked and
not ignored by Git. Root files, dot-directories, symlinks, tests, and placeholders
are excluded; simple Python package markers are indexed without semantic review.
Use `--include-tests` to include tests. Notebooks and other assets remain excluded.
The accompanying `example-*.config.json` demonstrates a faithful legacy-table port;
copy it only for a repository with that layout.

After changing configuration, start a new WORK with `--all` to regenerate area names,
tiers and library notes in existing summaries. Freshness checks track source content.
