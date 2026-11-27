---
description: Build and publish a pinned Linux/amd64 Docker image for Braingeneers Jobs
---

# Build and publish a container image

Build on NRP with GitLab CI and Kaniko. Follow the upstream
[`nrp-run` images guide](https://github.com/nrp-nautilus/sdsc-marketplace/blob/98bc617/plugins/nrp-nautilus/skills/nrp-run/references/images.md#build-in-nrp-gitlab-ci)
and use its Kaniko template as `.gitlab-ci.yml` in an authorized NRP GitLab
project with the Dockerfile and build context. Push the approved source to
start CI. Wait for the build to succeed, then take the commit-tagged image
reference from the project’s container registry.

Verify that the image includes Linux/amd64 and record its top-level registry
digest. Use `repository:tag@sha256:...` in the Job and report that pinned
reference. If Docker Buildx is available, `docker buildx imagetools inspect`
reads the manifest from the registry without building locally.

## Explicit local fallback

Use local Docker only when the user explicitly approves it for this build.
Set `IMAGE_REPO` to an authorized registry repository and `IMAGE_TAG` to a
release or source revision. Verify and pin the result using the same steps.

```bash
docker buildx build --platform=linux/amd64 --push \
  --tag "${IMAGE_REPO:?set IMAGE_REPO}:${IMAGE_TAG:?set IMAGE_TAG}" .
```
