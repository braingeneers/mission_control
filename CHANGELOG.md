2026-07-16 12:24 | workflows service | pin compact artifact labels and responsive artifact presentation release
2026-07-16 11:43 | workflows service | pin concurrent task progress and Quick Configure tooltip release
2026-07-16 10:45 | legacy Ephys services | retain the retired listener, scanner, and mxwdash definitions as commented Compose reference
2026-07-16 10:36 | service releases | pin the MQTT-enabled Workflows and Data Uploader image releases
2026-07-16 10:11 | workflow MQTT launch | enable the Workflows backend listener and remove the unused standalone launcher
2026-07-16 10:11 | data uploader | route selected workflow requests through the internal MQTT broker
2026-07-16 09:30 | workflows service | pin the full-width active progress sweep release
2026-07-15 17:00 | workflows service | pin explicit task-log selection and resilient reconciliation release
2026-07-15 14:54 | workflows service | pin the task-label formatting and transient scheduling triage release
2026-07-15 13:30 | workflows service | pin the Nextflow 26 runtime and live workflow version and startup-status release
2026-07-15 12:27 | workflows service | pin the combined Ephys run release with per-recording task fan-out and artifact links
2026-07-15 11:16 | workflows service | configure the public GitHub App ID in Compose while keeping only the private key in secrets
2026-07-15 10:50 | workflows service | pin the versioned-catalog release with private GitHub App definition refreshes
2026-07-15 10:00 | workflows service | wire organization-owned read-only GitHub App credentials for workflow definition refreshes
2026-07-15 09:33 | workflows service | pin the frontend release restoring distinct Dashboard and Workflows routes
2026-07-15 09:25 | workflows service | pin the dashboard-linked and layout-verified frontend release
2026-07-14 21:10 | workflows service | temporarily disable mqtt-job-listener in production compose via optional profile
2026-07-14 20:57 | workflows service | bump Workflows images for post-migration search_path init startup fix
2026-07-14 20:40 | workflows service | bump Workflows service image pins to include database schema bootstrap fix
2026-05-23 12:00 | docs | document mission-control-services-management skill usage
2026-05-23 12:05 | services | add scheduled data lifecycle backup service
2026-05-23 12:17 | service guidance | clarify image-owned code and portable Mission Control wiring
2026-05-27 17:00 | service-proxy | add websocket upgrade handling for search service
2026-05-27 18:00 | data-explorer | run metadata index refresh every 2 hours
2026-05-27 18:03 | data-explorer | run metadata index refresh every hour
2026-05-27 18:05 | data-explorer | keep compose service wiring minimal
2026-05-27 18:12 | services | remove legacy search service
2026-06-16 14:36 | maxwell-dashboard | update service image to v0.85 for parameter wording refresh
2026-06-24 16:27 | ephys services | update listener and dashboard service images to v0.86
2026-07-11 14:33 | workflows service | added workflows.braingeneers.gi.ucsc.edu Compose services using Docker Hub images and secret-fetcher wiring
2026-07-11 14:46 | shared services | introduced shared internal Mission Control Postgres for service clients
2026-07-11 15:51 | shared services | renamed the internal SQL service and added local/replicated volume standards with rolling database backups
2026-07-11 16:17 | shared services | packaged SQL database backups into the owning service image and clarified Compose service guidance
2026-07-11 17:14 | shared services | renamed the restart-persistent shared volume from cache to local
2026-07-11 17:22 | shared services | clarified sql-db as shared infrastructure instead of client-specific service wiring
2026-07-11 17:38 | shared services | aligned sql-db replicated backup temp files with dot-prefixed publish convention
2026-07-12 18:20 | data lifecycle backup | mount replicated volume for daily NRP/S3 sync
2026-07-11 18:19 | service guidance | documented dot-prefixed temporary publish convention for replicated volume writes
2026-07-13 11:34 | shared SQL service | documented schema-isolated client onboarding and reusable service-creation guidance
2026-07-13 12:18 | shared SQL service | add fail-closed schema selection guardrail, validation, and gated rollout guidance
2026-07-13 12:22 | shared SQL service | make schema guidance client-agnostic and remove transitional public-schema history
2026-07-14 10:25 | shared SQL service | document stable application schema names and the workflows ownership mapping
2026-07-14 10:31 | workflows service | select the owned workflows schema in published backend and frontend deployment images
2026-07-14 10:34 | shared SQL service | publish and pin the fail-closed client-schema guardrail image
2026-07-14 13:22 | workflows service | update Mission Control image pins to the latest workflow build tag
2026-07-14 20:45 | workflows service | repointed Mission Control images to the corrected backend startup-fix release
2026-07-14 21:15 | workflows service | pinned the responsive live Nextflow-stage backend release
2026-07-14 21:30 | workflows service | pinned guarded Alembic baselining for existing workflow schemas
2026-07-15 15:42 | workflows service | deploy generic task-label UI and concise Ephys workflow task tags
