# NRP-Hosted LLMs In Kubernetes Jobs

Use this reference when an NRP Kubernetes Job calls the managed open-weight LLM service. This is remote inference: the Job is an API client and does not need a GPU unless its own non-LLM work requires one.

## Verify current NRP behavior

Use upstream `nrp-llm` → Choosing a model, Fair-use limits, and Request
settings that matter for discovery, endpoint, context and concurrency limits.
Before choosing a model or concurrency policy, verify the current
[managed LLM documentation](https://nrp.ai/llms/) and
[live model status](https://nrp.ai/llm-status). Resolve model IDs at validation
or startup because the catalog changes.

## Braingeneers Secret Contract

The Braingeneers namespace already has the operator-owned Secret and key:

- Secret: `nrp-llm-api-key`
- Key: `nrp_llm_api_key`
- Application environment variable: `OPENAI_API_KEY`

Inject it directly into the Pod template:

```yaml
env:
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: nrp-llm-api-key
        key: nrp_llm_api_key
```

Never create, patch, replace, copy, decode, or print this Secret. Confirm only that the Secret and key exist when troubleshooting. If either is absent, stop and ask a Braingeneers namespace operator to restore the operator-owned credential. Do not place the token in a manifest, image, command argument, shell trace, workflow parameter, log, or chat.

For a Nextflow Kubernetes process, use the equivalent task-scoped mapping:

```groovy
pod = [
    [env: 'OPENAI_API_KEY', secret: 'nrp-llm-api-key/nrp_llm_api_key'],
]
```

Inject the key only into processes that call the API. Keep the Secret name and key configurable when authoring a reusable workflow.

## Client configuration

Keep the base URL and model configurable and use an explicit timeout.
See upstream `nrp-llm` for the client example and output-token settings.
Disable client retries when the application owns retry classification and durable resume.

## Cache Isolation And Data Handling

Follow upstream `nrp-llm` for `cache_salt` settings. For an unattended workflow, a stable HMAC-SHA256 derived from the API key plus a workflow-specific constant provides per-workflow isolation without another stored secret. Never log the salt or key.

Send only data permitted by the NRP acceptable-use policy and the application's own data policy. Avoid credentials, personal information, unpublished results, and other sensitive content unless the applicable policy explicitly allows it.

## Batch Reliability

- Retry connection failures, timeouts, HTTP 408/409/425, 429, and 5xx responses with exponential backoff and jitter. Do not retry authentication, authorization, invalid-model, or malformed-request failures without changing configuration.
- Bound retries inside one request loop, persist each successful result, then fail with a distinct retryable outcome so the workflow or Job layer can resume. Do not keep a broken Job alive with `sleep infinity`.
- Validate structured responses before accepting them. On retry, state the validation failure without logging raw prompts, response bodies, headers, or credentials.
- Cache successful results using keys that include the model, prompt/schema version, relevant input hashes, and any date or configuration that changes the answer. Do not publish partial final output when required calls remain unresolved.

The `grant-opportunities-report` workflow in the sibling Workflows repository applies these rules with task-scoped Secret injection, explicit model/base-URL parameters, HMAC-derived cache isolation, response validation, categorized request retries, immediate durable caching, and bounded Nextflow task retries.
