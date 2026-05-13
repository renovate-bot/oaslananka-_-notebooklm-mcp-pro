# Technical Debt Register

This register keeps follow-up work visible without mixing it into unrelated
feature changes.

## Supply Chain

| Item | Impact | Current handling |
|---|---|---|
| OpenSSF Best Practices badge | Scorecard `CII-Best-Practices` remains low until an application exists. | Public docs now describe the gap; badge application requires maintainer account work. |
| Fuzzing runtime expansion | Current fuzzing targets settings validation only. | ClusterFuzzLite and a Python Atheris target are configured; add protocol-level fuzzers as the server surface grows. |
| Multi-organization contributors | Scorecard `Contributors` remains low for a single-maintainer project. | CONTRIBUTING documents onboarding; community growth is not code-only work. |
| Project age | Scorecard `Maintained` remains low while the repository is less than 90 days old. | Weekly workflows and Dependabot activity establish maintenance history over time. |

## Architecture

| Item | Impact | Current handling |
|---|---|---|
| Import boundary enforcement | Humans and agents can accidentally cross layer boundaries. | `docs/ARCHITECTURE.md` defines boundaries; a future structural lint can enforce them. |
| Runtime observability | HTTP server has health checks but no full local metrics/tracing stack. | Structured logs and audit logs exist; metrics/tracing can be added without changing tool APIs. |
| OAuth provider breadth | GitHub OAuth is supported; other providers are not. | Additional providers should be added behind the same auth middleware boundary. |

## Operations

| Item | Impact | Current handling |
|---|---|---|
| Release signing for historical assets | Existing releases need signing bundles to improve Scorecard `Signed-Releases`. | `Sign Release Artifacts` workflow signs a selected existing release tag. |
| Branch protection strictness | Full Scorecard credit requires strict review settings and a token that can read branch protection metadata. | Branch protection is managed through repository settings and should stay aligned with required checks. |
| Human review evidence | Scorecard `Code-Review` requires review history that cannot be created by repository files alone. | Branch settings can enforce future reviews; current score improves only after reviewed PRs are merged. |
