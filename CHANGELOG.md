# Changelog

All notable changes to VMGA will be documented here.

## Unreleased

- Added npm Dependabot coverage for the OpenClaw integration.
- Documented upstream OpenClaw dependency advisory handling.
- Switched the repository to GitHub default CodeQL setup.

## v0.2.0 - 2026-06-10

- Added the production-alpha VMGA broker scaffold for governed Gmail and
  Workspace actions.
- Added proposal, approval, policy, state, evidence, ledger, executor, and
  broker modules with compatibility exports for the original adapter.
- Added JSON schemas for VMGA proposals, approvals, and evidence records.
- Added broker endpoints for proposals, approvals, and executions, including
  legacy compatibility routes.
- Added fake Gmail and gogcli-backed backend paths with shell-free subprocess
  execution.
- Added VMGA CLI entry points for broker operation, evidence verification,
  release checks, and approval-token workflows.
- Added dry-run and release evidence generation with verifier support.
- Added Hermes integration manifests, schemas, tool handlers, and skill docs.
- Added OpenClaw plugin packaging, profile adapter, examples, and validation
  scripts.
- Hardened broker operations with SQLite WAL mode, correlation IDs, in-memory
  redaction, bounded approval tokens, evidence lifecycle guidance, strict mock
  schemas, live-smoke cleanup tagging, and Gmail rate-limit backoff.
- Added open-source readiness scaffolding for packaging, CI, security reporting,
  contribution guidance, release checklists, evidence docs, and DSOVS
  self-assessment.
- Added the MIT License.

## Earlier

- Started standalone VMGA repository extraction.
- Imported the v0.2 reference adapter, policies, specification, and tests.
- Hardened VMGA policy validation, denial error codes, and approval binding
  checks for production-alpha work.
