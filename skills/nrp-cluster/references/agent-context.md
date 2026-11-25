# Braingeneers NRP agent commands

- [Build and push](../.agent/workflows/build-push.md) for the pinned image.
- Use `bash run_pipeline_local.sh` inside the image for a local smoke check.
- Use the project's `run_job.sh` and `jobdefinition.yaml` to identify render
  variables. Review existing scripts for direct apply and credential substitution
  before using them. Follow the [deploy workflow](../.agent/workflows/deploy-job.md)
  for preflight, dry-run, and submission.
- Use the [monitor workflow](../.agent/workflows/monitor-job.md) for explicit
  context, namespace, and owner-scoped cleanup.

See [template layout](readme.md) for project files and [lab setup](nrp_setup.md)
for paths and credential wiring. Upstream `nrp-run` covers generic Job operation.
