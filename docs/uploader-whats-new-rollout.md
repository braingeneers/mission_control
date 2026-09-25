# Uploader-dev announcements and layout — September 25, 2026

Candidate image: `braingeneers/braingeneers-data-uploader:20260925-6750199f246c`.
The older `uploader` service and both hostnames stay unchanged. This update only recreates
`uploader-dev`; no Workflows, notification, proxy, or database restart is required.

## Changes

- Upload only has the same hover/keyboard/touch purpose help as saved Recipes.
- Upload stays beside the progress area, below the Recipe list on narrow screens.
- `/admin` edits and previews What’s new, enables/disables it, saves new versions, and resets
  dismissals for one email or everyone. The initial user-facing message is seeded **disabled**.

Announcement content and email-keyed, version-specific dismissals live at
`/replicated/uploader-dev/whats-new` through `WHATS_NEW_DIR`, on the existing backed-up volume.
Preserve this directory and mount when the operator eventually moves uploader-dev to the main
domain. That domain move is a separate operation. No data migration is part of this release.

## Operator recreation

Run on the server from the Mission Control checkout, outside active uploader-dev uploads:

```bash
git pull --ff-only
docker compose pull uploader-dev
docker compose up -d --no-deps --wait uploader-dev
make verify-uploader-deployment SERVICE=uploader-dev
```

The verifier must report the configured image running and anonymous API requests returning the
expected JSON authentication response. Refresh the browser afterward.

## Review before enabling

1. Open `https://uploader-dev.braingeneers.gi.ucsc.edu/admin`. Expect **Version 1 · Disabled** on
   first initialization. Later recreations preserve the existing saved state instead.
2. Edit the title and message, then use **Preview**. Preview never marks the message seen.
3. Use **Save changes** to retain the version and existing dismissals. It also saves the enabled
   checkbox; leave it unchecked until the message is ready for users.
4. When ready, check **Enable for users** and save. The enabled message appears on the next visit
   until dismissed by Got it, the close button, or Escape. What’s new beside Help reopens it.
5. **Save as new version** makes everyone eligible again while preserving the selected enabled
   state. **Reset for email/everyone** applies only to the current version, takes effect on the next
   visit, and never enables a disabled announcement. Reset the reviewing user if needed before launch.

The existing private-proxy `/admin` access policy is unchanged. Ordinary users never submit an
email for dismissal; it comes from their trusted header. Separate browsers share the receipt.
There is no popup polling that interrupts active uploads, and announcement failures do not block
ordinary uploader work.

Previous candidate image for rollback: `20260925-66add91984c8`. Retain announcement storage if
rolling back; the older image simply does not use it. Do not delete or reset state to roll back.
