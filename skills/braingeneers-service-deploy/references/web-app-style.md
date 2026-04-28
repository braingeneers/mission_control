# Braingeneers Web App Style

Use this reference when a `mission_control` service includes a browser-facing UI. The goal is visual consistency with existing Braingeneers agent-built apps, not a rigid component library.

## Source Apps

Review these local sibling repos when available, or locate their equivalents in GitHub if the local paths differ:

- `data-lifecycle`: deletion review and operational workflow UI.
- `data_uploader`: staged upload workflow with metadata editing, progress, help, and admin views.
- `data-explorer`: dataset search, summaries, details, and download actions.

Common source files to inspect:

- `static/styles.css` or app-specific static CSS.
- `static/index.html` and any admin/detail HTML views.
- Static image assets such as Braingeneers logo marks and brain illustrations.

## Visual Direction

Build operation-focused web apps, not generic dashboards or marketing landing pages.

- Use a dark, high-contrast interface with layered panels, subtle gradients, and clear status states.
- Prefer dense, scannable layouts for lab operations: cards for summaries, tables or lists for data, and compact action rows for repeated tasks.
- Keep the copy practical and specific. Labels should tell users what action they can take, what state the system is in, and what risk exists.
- Avoid default white pages, unstyled Bootstrap-like layouts, and generic purple SaaS themes.

## Typography

The current apps consistently use Google Fonts:

```css
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap");
```

Use:

- `Space Grotesk` for app titles, section headings, brand kickers, and strong numeric summaries.
- `IBM Plex Sans` for body text, forms, tables, and controls.
- `IBM Plex Mono` only when code, UUIDs, paths, hashes, or identifiers benefit from monospaced rendering.

If external font loading is not appropriate for a service, keep the same typographic roles with local or system fallbacks.

## Color Tokens

Use one of these palettes as a starting point, then adjust only when the service has a clear domain reason.

Data Explorer and Data Lifecycle:

```css
:root {
  --bg: #0f1419;
  --panel: #172028;
  --panel-2: #1d2832;
  --panel-3: #111921;
  --text: #e9f0f5;
  --muted: #9fb1bf;
  --line: #2a3b47;
  --accent: #4ec2f0;
  --green: #2bd3a6;
  --gold: #f2b36b;
  --danger: #f06d6d;
}
```

Data Uploader:

```css
:root {
  --bg: #0b0f12;
  --bg-accent: #141c21;
  --ink: #f3f3f1;
  --muted: #a5b0b5;
  --card: #12181d;
  --accent: #f15a3a;
  --accent-2: #2fc4b2;
  --accent-3: #f5b02e;
  --stroke: rgba(243, 243, 241, 0.12);
}
```

Use semantic aliases in new apps when possible: `--success`, `--warning`, `--danger`, `--surface`, `--surface-raised`, and `--border`.

## Layout Pattern

Use a single app shell with generous outer spacing and constrained width:

```css
main,
.page-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}
```

Common structure:

- Hero/header with an eyebrow or brand kicker, a direct `h1`, a short lede, and optional logo/status controls.
- Primary workflow sections in `.panel` cards with rounded corners, subtle borders, and shadows.
- Split panels for two related workflows, such as list plus detail or source plus configuration.
- Summary cards for counts, health, storage, queued work, or other quick-read state.
- Tables and list rows for operational data; use horizontal overflow rather than hiding columns.
- Help content at the bottom or behind contextual affordances, not as the main interface.

## Component Guidance

Buttons:

- Use pill-shaped primary actions for high-level actions.
- Use outlined or ghost buttons for secondary actions.
- Use warning or danger colors only for destructive or irreversible actions.
- Keep disabled states visually obvious and explain the missing prerequisite nearby.

Forms:

- Use uppercase, spaced labels for compact field scanning.
- Keep inputs on dark surfaces with clear borders.
- For metadata-heavy forms, group fields into tabs or sections and provide raw JSON/debug views when useful.

Status:

- Use small chips for workflow state, auth state, health, queued work, and risk labels.
- Pair color with text; do not rely on color alone.
- Use progress bars and spinners only for real asynchronous work.

Help and safety:

- Use tooltips sparingly for domain terms or disabled actions.
- For destructive operations, include clear review states and confirmation language.
- For upload, delete, or secret-related flows, show what will happen before the user commits.

Motion:

- Use subtle `slideUp` or `floatIn` entrance motion for panels.
- Respect `prefers-reduced-motion`.
- Avoid decorative motion that competes with operational status.

## Backgrounds

The existing apps use dark radial gradients instead of flat backgrounds:

```css
body {
  background:
    radial-gradient(circle at top left, rgba(78, 194, 240, 0.14), transparent 34%),
    radial-gradient(circle at right, rgba(43, 211, 166, 0.12), transparent 28%),
    var(--bg);
}
```

This creates continuity across tools without requiring the same exact colors. Keep gradients subtle enough that tables, forms, and code blocks remain readable.

## Assets

This skill bundles small reusable assets in `assets/`:

- `assets/braingeneers_logo.png`: copied from the data uploader UI.
- `assets/big-brains.png`: copied from the data explorer UI.

Use these only when they fit the app. Prefer a small header mark, corner illustration, or empty-state graphic; do not make the asset compete with operational controls.

When working in another repo, copy assets into that service's own `static/` or frontend asset directory and reference them with service-local paths. Do not reference files directly out of the skill directory from production code.

## Accessibility And Responsiveness

Minimum expectations:

- Use semantic headings and labels.
- Preserve visible focus states.
- Support keyboard operation for primary workflows.
- Ensure layouts collapse cleanly below `720px`.
- Keep contrast high on dark surfaces.
- Add `aria-live` or equivalent announcements for async status when users depend on progress or completion messages.

## Implementation Checklist

Before handing off a new web UI:

- The page has the Braingeneers dark operational visual language.
- The typography uses the established display/body pairing or an intentional fallback.
- The main workflow is visible without reading long instructions.
- Error, empty, loading, success, and disabled states are styled.
- Tables/lists remain usable on mobile or narrow windows.
- Any copied assets live inside the target service repo.
- The UI has been checked with the service's deployment path, including proxy prefix or direct port behavior if applicable.
