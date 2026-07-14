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
