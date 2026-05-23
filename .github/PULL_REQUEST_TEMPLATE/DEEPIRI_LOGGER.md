IMPORTANT:

PR must be opened from your personal branch → dev
You must tag @Team-Deepiri/support-team
You must update Plaky to "Needs QA"
Never move a task to "Done" (Done = production release only)

Description
This PR publishes the standalone deepiri-logger repository contents into the platform PR so the platform can switch to consuming a canonical, versioned logger repo. It contains the logger foundation (schema, PII rules, SDKs, tooling, and docs) implemented in this repository.

Related Issue number: TBD
Plaky feature name: Deepiri Logger (backend)
Component, feature, or system affected: deepiri-logger standalone repo (schema, SDKs, tooling)
Purpose of change: extract and centralize logger foundation into a standalone repo for independent development and releases

Changes
List the most important updates included in this repository (what we implemented here):

- Added canonical schema and PII patterns: shared/schema.json, shared/pii-patterns.yml
- Implemented Python SDK: python/deepiri_logger/ with init() and masking processor
- Implemented Node SDK: nodejs/ formatter, Express middleware, and examples
- Added Rust scaffold: rust/ with tracing subscriber JSON formatter
- Added parity validator and tooling: scripts/validate_parity.py
- Added language adapter stubs: C++, Ruby, Bash
- Added CI integration: .github/workflows/ci.yml to run parity checks
- Added docs and rollout helpers: ROLLOUT.md, COMPLETION_CHECKLIST.md
- Added packaging/publish helper scripts (placeholders) and examples

Be specific. Include:

New or updated functions, services, components, or scripts:

- python/deepiri_logger/init() and masking processor
- nodejs/createLogger() and nodejs/middleware.requestLogger()
- scripts/validate_parity.py (schema + masking validator)

Refactoring or structural improvements:

- Centralized logging schema and masking rules so SDKs share a single contract

Dependency or configuration changes:

- CI job added to run parity validator across Python/Node

No runtime service code changed in this repo (service-by-service integrations are covered in follow-up PRs)

Any significant implementation details:

- The parity validator enforces shared/schema.json and shared/pii-patterns.yml
- Both Python and Node SDKs auto-generate trace_id when absent
- Packaging/publishing of language packages is supported via helper scripts (not executed in this PR)

Related
Issue: TBD
Plaky: Deepiri Logger (backend)
Related PRs (optional): N/A — this is the standalone repo content PR

Testing
How I verified the changes and how to test locally:

- Ran scripts/validate_parity.py to confirm Python/Node outputs conform to shared/schema.json and PII masking rules
- Confirmed nodejs builds via TypeScript compile and python SDK imports inside a virtualenv
- CI will run the same parity checks to prevent regressions

Additional testing details:

- No service runtime behavior changes in this PR; follow-up service PRs will replace local logger code and verify integration

Important Notes (Optional)
Known limitations:

- This PR delivers the standalone logger repository contents only; integrating the submodule into platform services happens in subsequent platform PR(s)
Blockers:
- None for the standalone-repo objective

Workflow Checklist (Required)

- Branch is up to date with dev
- PR is from your branch → dev
- PR title follows convention (feat:, refactor:, etc.)
- Plaky feature/bug name included above
- Tagged @Team-Deepiri/support-team
- Plaky task moved to "Needs QA"

Review Requests

@Team-Deepiri/support-team
