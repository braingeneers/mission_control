# Braingeneers Web App Style

Use this reference only for a new or materially refreshed browser UI. Preserve
an established application's own design system during ordinary maintenance.

## Inspect Before Designing

Review the owning app and nearby active Braingeneers interfaces, especially
`data_uploader` and `data-explorer`, when available locally. Inspect their
actual HTML, CSS, components, responsive behavior, and assets rather than
copying a screenshot or assuming this reference is a rigid component library.

The target is an operations-focused lab tool: practical, dense enough to scan,
and visually consistent with adjacent services. It is not a marketing page or
generic SaaS dashboard.

## Visual Language

- Dark, high-contrast surfaces with restrained radial gradients.
- Layered panels, compact action rows, clear tables/lists, and visible status.
- Direct labels that explain action, state, prerequisite, and risk.
- Accent colors reserved for interaction and semantic status rather than
  decoration.
- Motion limited to subtle state transitions and respectful of
  `prefers-reduced-motion`.

Preferred typography roles:

- `Space Grotesk` for titles, headings, and strong numeric summaries.
- `IBM Plex Sans` for body copy, forms, tables, and controls.
- `IBM Plex Mono` only for code, UUIDs, paths, and hashes.

Use local or system fallbacks when external font loading is inappropriate.

## Starting Tokens

Data Explorer provides the neutral blue/green baseline:

```css
:root {
  --bg: #0f1419;
  --surface: #172028;
  --surface-raised: #1d2832;
  --text: #e9f0f5;
  --muted: #9fb1bf;
  --border: #2a3b47;
  --accent: #4ec2f0;
  --success: #2bd3a6;
  --warning: #f2b36b;
  --danger: #f06d6d;
}
```

Data Uploader's orange/teal palette is an alternative when the workflow needs a
warmer primary action. Keep semantic aliases even when colors change.

A subtle background treatment is sufficient:

```css
body {
  background:
    radial-gradient(circle at top left, rgba(78, 194, 240, 0.14), transparent 34%),
    radial-gradient(circle at right, rgba(43, 211, 166, 0.12), transparent 28%),
    var(--bg);
}
```

## Layout And Components

Use one centered application shell:

```css
.page-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}
```

Choose components by workflow:

- Header: brand kicker, direct `h1`, short lede, and optional status/actions.
- Panels: related workflow steps or list/detail splits.
- Summary cards: only for high-value counts, health, storage, or queued work.
- Tables/lists: repeated operational data; preserve columns with horizontal
  overflow or responsive cards rather than silently hiding information.
- Buttons: strong primary action, outlined secondary action, and danger styling
  only for destructive or irreversible behavior.
- Forms: compact labels, grouped fields, clear validation, and nearby
  explanations for disabled controls.
- Status: text plus color, small chips, and progress indicators only for real
  asynchronous work.
- Help: contextual or secondary to the main workflow.

For destructive, upload, delete, retention, or secret-related flows, show the
exact target and consequence before commitment.

## Accessibility And Responsive Behavior

Minimum expectations:

- semantic headings, labels, and landmarks;
- visible focus and keyboard access for primary workflows;
- sufficient contrast and status text that does not rely on color alone;
- `aria-live` or equivalent announcements for important async changes;
- clean collapse below roughly `720px`;
- usable long identifiers and tables on narrow screens.

Design explicit loading, empty, success, failure, disabled, and degraded states.

## Bundled Assets

The skill contains:

- `assets/braingeneers_logo.png`
- `assets/big-brains.png`

Use an asset only when it supports the workflow, such as a small header mark or
empty-state illustration. Copy it into the owning service's asset directory;
production code must not reference the skill directory.

## Verification

- The main workflow is understandable without long instructions.
- Copy and status treatment match actual behavior and risk.
- Keyboard, focus, responsive, and async states work.
- The UI is checked through the real deployment path, including proxy prefixes,
  authentication, timeouts, and websocket behavior when applicable.
- Any borrowed asset or design token now belongs to and is maintained by the
  owning service repository.
