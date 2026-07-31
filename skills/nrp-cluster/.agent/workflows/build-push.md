---
description: Build Docker image and push to Docker Hub for NRP deployment
---

# Build & Push Docker Image

// turbo-all

1. Build the Docker image for linux/amd64:
```powershell
docker buildx build --platform=linux/amd64 -t hitpunch/nrp_template:latest . 2>&1
```

2. Push the image to Docker Hub:
```powershell
docker push hitpunch/nrp_template:latest 2>&1
```

3. Verify the push succeeded by checking the output for the digest line (e.g. `latest: digest: sha256:...`).

4. Report back to the user with the image digest.
