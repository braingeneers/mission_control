# Brave Search In Kubernetes Jobs And Workflows

Use this reference when an NRP Kubernetes Job or workflow task calls the Brave Search API.

## Verify Current Brave Behavior

Keep request syntax and vendor-specific behavior in the official documentation:

- Authentication: https://api-dashboard.search.brave.com/documentation/guides/authentication
- Web Search API: https://api-dashboard.search.brave.com/api-reference/web/search/get
- Pricing: https://api-dashboard.search.brave.com/documentation/pricing

Verify pricing and terms before planning recurring usage. The current Search price is $5 per 1,000 requests with $5 in free credits each month, making the current free monthly allowance approximately 1,000 Search requests.

## Braingeneers Secret Contract

The credential is maintained in the operator-owned Braingeneers secrets repository and is available to jobs and workflows through the existing Kubernetes Secret:

- Secret: `brave-search-api`
- Key: `brave-search-api`
- Application environment variable: `BRAVE_SEARCH_API_KEY`

Inject it with `secretKeyRef` only into containers that call Brave Search. For a Nextflow Kubernetes process, use the task-scoped mapping:

```groovy
pod = [
    [env: 'BRAVE_SEARCH_API_KEY', secret: 'brave-search-api/brave-search-api'],
]
```

Never create, patch, replace, copy, decode, retrieve, print, or log this Secret. If it is absent, stop and ask a Braingeneers namespace operator to restore the operator-owned credential.

## Shared Request Budget

Treat the current free monthly allowance as one account-wide budget shared by all users, jobs, and workflows. Keep aggregate planned usage substantially below 1,000 requests per month, and give each workload only a small fraction of that shared allowance.

- Set an explicit per-run request budget that counts initial attempts, retries, and pagination.
- Cache and reuse safe results, avoid duplicate queries, and stop or degrade cleanly when the budget is exhausted.
- Check current pricing and coordinate with the user or operator before a workload could consume a material share of the monthly allowance.

The `workflow-sources/grant-opportunities-report/` implementation in the sibling `workflows` repository is the working Braingeneers reference for task-scoped Secret injection and a retry-inclusive request budget.
