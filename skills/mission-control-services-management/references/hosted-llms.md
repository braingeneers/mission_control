# NRP-Hosted LLMs For Mission Control Services

Use this reference when a Docker Compose service on `braingeneers.gi.ucsc.edu` calls the NRP-managed open-weight LLM API. The model runs on NRP; do not add a GPU or local model server to the GI host for this pattern.

## Verify Current NRP Behavior

The model catalog and fair-use limits rotate. Check the current official documentation before choosing a model, context size, or concurrency:

- Overview and access: https://nrp.ai/llms/
- API access and cache isolation: https://nrp.ai/documentation/userdocs/ai/llm-managed/api-access/
- Active models and capabilities: https://nrp.ai/documentation/userdocs/ai/llm-managed/models/
- Fair use: https://nrp.ai/documentation/userdocs/ai/llm-managed/fair-use/
- Model lifecycle: https://nrp.ai/documentation/userdocs/ai/llm-managed/lifecycle/
- Live model status: https://nrp.ai/llm-status

Use the OpenAI-compatible base URL `https://ellm.nrp-nautilus.io/v1`. Discover active IDs through `/v1/models`; do not copy the rotating model list into this skill. Treat `gpt-oss` as an example rather than a permanent default.

## Braingeneers Secret Contract

The existing operator-owned Kubernetes Secret is:

- Secret: `nrp-llm-api-key`
- Key: `nrp_llm_api_key`
- Fetched file: `/secrets/nrp-llm-api-key/nrp_llm_api_key`

Do not create, patch, replace, decode, print, or log this Secret. If it is absent, stop and ask a Braingeneers namespace operator to restore the operator-owned credential. `secret-fetcher` materializes it into the shared in-memory `secrets` volume. A consuming service needs:

```yaml
environment:
  NRP_LLM_BASE_URL: "https://ellm.nrp-nautilus.io/v1"
  NRP_LLM_API_KEY_FILE: "/secrets/nrp-llm-api-key/nrp_llm_api_key"
volumes:
  - secrets:/secrets
depends_on:
  secret-fetcher:
    condition: service_healthy
```

Define the `*_API_KEY_FILE` contract in the owning application and read the file directly when constructing the API client. If a library only supports `OPENAI_API_KEY`, have the owning image's entrypoint read the file and export the value immediately before `exec`; do not embed that shell logic or the token in Compose.

The existing `uploader-dev` service sets `NRP_LLM_API_KEY_FILE=/secrets/nrp-llm-api-key`. Its application intentionally accepts the Secret directory and resolves the key inside it. Preserve that app-specific contract when updating `uploader-dev`; prefer the exact key file for new services.

The NRP LLM token is unrelated to the Braingeneers Auth0 service-account JWT and to MCP bearer-token validation. Do not substitute one credential for another.

## Application Behavior

- Keep endpoint, model, timeouts, output-token bounds, and retry policy in the owning service repo and image. Compose should normally contain only the deployment-specific endpoint and secret-file path.
- Confirm the configured model appears in `/v1/models` at startup or before an operation. Surface model unavailability without exposing request headers or the token.
- For an optional LLM feature, keep the rest of the service healthy when the token, model, or API is unavailable and report only that the feature is disabled. For a required capability, fail readiness with a sanitized diagnostic.
- Retry connection failures, timeouts, HTTP 408/409/425, 429, and 5xx responses with exponential backoff and jitter. Do not retry authentication, authorization, invalid-model, or malformed-request failures without a configuration change.
- Follow the current NRP fair-use page and reduce concurrency when latency rises. Never set maximum output tokens equal to the full model context window.
- Validate structured responses before use. Do not log prompts, full responses, raw HTTP error bodies, authorization headers, API keys, or private cache salts.

## Cache Isolation

Set `extra_body.cache_salt` when prompts or responses must not share prefix caches with other users of the tenant. Use a secret base64-encoded value representing at least 256 bits. A stable HMAC-SHA256 derived from the API key plus a service-specific constant provides application-level isolation without another stored secret. Never expose the derived value.

The sibling `../workflows/workflow-sources/grant-opportunities-report/` implementation is the working Braingeneers reference for OpenAI-client configuration, HMAC-derived cache isolation, schema validation, categorized transient retries, sanitized logging, and durable caching.

## Safe Validation And Rotation

Agent-side diagnosis remains local and read-only. Never SSH to the GI server or mutate Kubernetes Secrets. An operator may confirm that the mounted file is non-empty without printing it:

```bash
docker compose exec -T SERVICE test -s /secrets/nrp-llm-api-key/nrp_llm_api_key
```

After an operator rotates the Kubernetes Secret, instruct the operator to refresh `secret-fetcher`, verify it, and recreate only the consuming service on `braingeneers.gi.ucsc.edu`:

```bash
docker compose up -d --force-recreate secret-fetcher
docker compose logs --tail=100 secret-fetcher
docker compose up -d --force-recreate SERVICE
docker compose logs --tail=100 SERVICE
```

Application logs and health endpoints should report connectivity, selected model, and feature readiness without revealing token contents.
