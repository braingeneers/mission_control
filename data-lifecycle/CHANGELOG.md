2026-05-22 15:38 | docs | restructure README for backup operators and deletion web app users
2026-05-22 15:39 | backup pipeline | preserved slashful source keys and surfaced source access badkeys
2026-05-22 16:07 | validation skill | added two-run backup reprocessing check skill
2026-05-23 12:17 | backup service | add production scheduler entrypoint for Mission Control
2026-05-23 12:43 | backup service | include timezone in scheduler next-run log
2026-05-23 12:44 | backup service | show scheduler timezone as PST or PDT
2026-05-23 12:48 | backup service | make scheduler timezone logs consistent
2026-07-12 18:20 | backup service | add daily replicated volume sync to scheduled backup image
2026-08-17 21:00 | backup pipeline | make stage0-stage4 runtime inputs overrideable for stage-native Nextflow execution
2026-08-18 14:35 | backup pipeline | add Stage 3 memory heartbeats, comparison accounting, and a fail-before-upload majority guard
2026-08-18 17:20 | backup service | move the replicated-volume scheduler and sync implementation to mission_control
2026-08-20 | lifecycle | adopt zero-byte retention markers and monthly advisory report generator
2026-08-21 | v36 | move active workflow runtime and policy into mission_control/data-lifecycle and retire the web image
2026-08-21 | v38 | improve retention PDF layout and publish compact date-grouped Slack report text
