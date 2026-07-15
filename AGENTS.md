# AGENTS.md

## File Operations

- Use `trash` instead of `rm`.

## Service Operations

- Do not create, update, patch, replace, or delete Kubernetes Secrets. Secret mutations are operator-owned; provide the required instructions and wait for the operator to apply them.
- Do not run production-style `mission_control` services locally unless the user explicitly asks for a local test.
- Services such as `mqtt-job-listener`, `maxwell-dashboard`, and other Docker Compose managed lab services are intended to run on `braingeneers.gi.ucsc.edu`.
- When service restart, pull, recreate, or deployment operations are needed, instruct the user to handle them on the `braingeneers` server instead of running them from a local workstation.
