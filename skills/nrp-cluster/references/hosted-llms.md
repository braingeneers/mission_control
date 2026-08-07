# NRP-Hosted LLMs In Kubernetes Jobs

Use this reference when an NRP Kubernetes Job calls the managed open-weight LLM service. This is remote inference: the Job is an API client and does not need a GPU unless its own non-LLM work requires one.

## Verify Current NRP Behavior

The hosted catalog and limits change. Check the current official pages before choosing a model or concurrency policy:

- Overview and access: https://nrp.ai/llms/
- API access and cache isolation: https://nrp.ai/documentation/userdocs/ai/llm-managed/api-access/
- Active models and capabilities: https://nrp.ai/documentation/userdocs/ai/llm-managed/models/
- Fair use: https://nrp.ai/documentation/userdocs/ai/llm-managed/fair-use/
- Model lifecycle: https://nrp.ai/documentation/userdocs/ai/llm-managed/lifecycle/
- Live model status: https://nrp.ai/llm-status

The OpenAI-compatible base URL is `https://ellm.nrp-nautilus.io/v1`. List `/v1/models` at validation or startup time rather than copying the rotating catalog into job configuration. Treat `gpt-oss` as an example, not a permanent default.

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

## OpenAI-Compatible Client

Prefer the official OpenAI client or another OpenAI-compatible client. Keep the base URL and model configurable and set an explicit timeout:

```python
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ.get("NRP_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"),
    timeout=180,
    max_retries=0,
)
response = client.chat.completions.create(
    model=os.environ.get("NRP_LLM_MODEL", "gpt-oss"),
    messages=[{"role": "user", "content": "Summarize this record."}],
)
content = response.choices[0].message.content
# Validate and use content without logging sensitive inputs or outputs.
```

Disable client retries when the application owns retry classification and durable resume. If using `max_tokens` or `max_output_tokens`, keep it well below the selected model's context limit; never set it equal to the full context window.

## Cache Isolation And Data Handling

Set `extra_body.cache_salt` when prompts or responses must not share prefix caches with other users of the tenant. Use a secret base64-encoded value representing at least 256 bits. For an unattended workflow, a stable HMAC-SHA256 derived from the API key plus a workflow-specific constant provides per-workflow isolation without another stored secret. Never log the salt or key.

Send only data permitted by the NRP acceptable-use policy and the application's own data policy. Avoid credentials, personal information, unpublished results, and other sensitive content unless the applicable policy explicitly allows it.

## Batch Reliability

- Retry connection failures, timeouts, HTTP 408/409/425, 429, and 5xx responses with exponential backoff and jitter. Do not retry authentication, authorization, invalid-model, or malformed-request failures without changing configuration.
- Follow the current fair-use page. Reduce concurrency when latency increases, and use one request at a time for large-context calls when required.
- Bound retries inside one request loop, persist each successful result, then fail with a distinct retryable outcome so the workflow or Job layer can resume. Do not keep a broken Job alive with `sleep infinity`.
- Validate structured responses before accepting them. On retry, state the validation failure without logging raw prompts, response bodies, headers, or credentials.
- Cache successful results using keys that include the model, prompt/schema version, relevant input hashes, and any date or configuration that changes the answer. Do not publish partial final output when required calls remain unresolved.

The working `../workflows/workflow-sources/grant-opportunities-report/` example applies these rules with task-scoped Secret injection, explicit model/base-URL parameters, HMAC-derived cache isolation, response validation, categorized request retries, immediate durable caching, and bounded Nextflow task retries.
