---
title: "feat: VMGA full production and open-source gambit"
type: feat
status: active
date: 2026-06-09
origin: docs/plans/2026-06-09-001-feat-vmga-production-open-source-plan.md
---

# feat: VMGA full production and open-source gambit

## Summary

VMGA should become a standalone, open-source Gmail governance component that
agents can use without receiving direct mailbox write authority. The full gambit
is to ship three things together:

- A reliable VMGA core with proposal validation, policy, approval binding,
  execution gating, state, and evidence.
- Integration surfaces for Hermes and OpenClaw that are usable while preserving
  clear bypass-closure requirements.
- Release and deployment evidence that lets adopters understand exactly when
  VMGA is hard enforcement versus advisory governance.

The hard line remains unchanged: agents may reason about mail, but Gmail side
effects must pass through VMGA-controlled policy, approval, execution, and
evidence paths that the agent cannot rewrite or bypass.

## Current Baseline

The standalone repo already has:

- A Python package in `src/vmga/`.
- The main reference implementation in `src/vmga/vmga_adapter.py`.
- Minimal local governance models in `src/vmga/models.py`.
- Policy profiles in `policies/`.
- A unit test suite in `tests/test_vmga_adapter.py`.
- Integration/security docs for Hermes and OpenClaw in `docs/`.
- Open-source basics: README, MIT license, security policy, contribution guide,
  changelog, CI, CodeQL, and Dependabot.

Recent work hardened policy validation, stable denial codes, approval binding,
and documentation around Hermes/OpenClaw bypass surfaces. The repo is ready to
move from documentation-hardening into implementation-hardening.

## Requirements

- R1. VMGA must validate versioned Gmail proposals before policy evaluation.
- R2. VMGA must preserve deterministic proposal hashes across canonical fields.
- R3. VMGA must bind approvals to proposal hash, actor, action, thread, messages,
  recipients, attachments, expiration, and approver.
- R4. VMGA must fail closed when policy, approval state, execution state, or
  evidence writes are unavailable.
- R5. VMGA must support advisory library mode for local/dev use and clearly
  distinguish it from hard-enforced deployment mode.
- R6. VMGA must expose a broker boundary suitable for Hermes and OpenClaw, where
  Gmail credentials and VMGA verifier secrets are outside the agent process.
- R7. Hermes integration must use a shell-free plugin tool surface and must not
  rely on Hermes dangerous-command approvals as VMGA approval.
- R8. OpenClaw integration must treat `/tools/invoke`, paired nodes, elevated
  exec, sandbox mounts, SecretRefs, and operator scopes as deployment controls,
  not proof of VMGA enforcement by themselves.
- R9. Direct Google Workspace CLIs, native Gmail tools, browser sessions, MCP
  servers, hooks, cron jobs, and plugins must be treated as bypasses unless they
  route through VMGA proposals and VMGA execution.
- R10. Evidence must be machine-readable and cover proposal, validation, policy,
  approval, execution, denial, lockdown, and reset paths.
- R11. Release checks must prove docs, examples, and policies do not overclaim
  prompt-injection prevention, DLP, host compromise protection, compliance, or
  security of Hermes/OpenClaw internals.
- R12. Public examples must be safe to publish: placeholder domains, fake tokens,
  no real mailbox content, no real account identifiers, and strict defaults.

## Key Decisions

- **Core before adapters:** Harden the VMGA core contract before writing rich
  Hermes/OpenClaw examples. Adapter demos are only trustworthy once the core gate
  is stable.
- **Broker is the production shape:** The production path should be a VMGA broker
  process or service. In-process imports remain useful for tests and demos, but
  hard-enforcement claims require separate credentials, verifier secrets, state,
  and evidence.
- **`gogcli` is the preferred optional Gmail backend reference:** It has safety
  knobs like no-send, read-only MCP defaults, and baked safety profiles. It can
  be used behind VMGA, not exposed directly to agents.
- **`googleworkspace/cli` is a high-power reference/backend candidate:** It is
  useful for auth and Workspace breadth, but direct `gws` access is a bypass and
  must be denied in Hermes/OpenClaw agent contexts.
- **Hermes plugin hooks are not the enforcement boundary:** Hooks are useful for
  observability or defense in depth. The hard boundary is VMGA broker plus
  credential isolation.
- **OpenClaw controls must be evidenced, not assumed:** SecretRefs, sandboxing,
  OpenShell, pairing, operator scopes, trusted-proxy auth, fs-safe, and
  `/tools/invoke` all require deployment evidence.
- **Docs stay claim-disciplined:** VMGA can be production-ready as a component
  while still requiring deployment controls outside the package.

## Architecture Target

```text
Agent runtime (Hermes/OpenClaw)
  -> VMGA adapter/plugin tool surface
  -> VMGA broker API
  -> Proposal validation
  -> Policy engine
  -> Approval verifier
  -> Gmail executor backend
  -> Evidence ledger/state store
```

The agent runtime receives proposal IDs, denial reasons, review status, and safe
read results. It does not receive Gmail OAuth refresh tokens, approval verifier
secrets, direct executor credentials, writable policy, writable VMGA state, or
raw evidence storage.

## Implementation Units

### U1. Split Contract, Policy, State, And Adapter Modules

- **Goal:** Move from a large `vmga_adapter.py` file toward clear package
  boundaries without changing behavior.
- **Requirements:** R1, R2, R4, R5
- **Files:** `src/vmga/vmga_adapter.py`, `src/vmga/models.py`,
  `src/vmga/proposals.py`, `src/vmga/policy.py`, `src/vmga/state.py`,
  `src/vmga/approvals.py`, `tests/test_vmga_adapter.py`,
  `tests/test_vmga_contract.py`
- **Approach:** Extract dataclasses and deterministic hashing first, then policy
  and state. Keep compatibility exports from `src/vmga/vmga_adapter.py` and
  `src/vmga/__init__.py` so existing tests and users do not break.
- **Patterns to follow:** Current `VMGAProposal.compute_hash()`,
  `VMGAPolicy.validate_rules()`, and `ApprovalRecord.from_proposal()`.
- **Test scenarios:**
  - Existing adapter tests continue to pass through compatibility imports.
  - Proposal hash output remains identical before and after extraction.
  - Unknown action and unknown policy fields still fail before evaluation.
  - Policy decisions still emit stable `rule_id` and `error_code`.
- **Verification:** `pytest tests/test_vmga_adapter.py tests/test_vmga_contract.py`.

### U2. Version The Proposal And Approval Contracts

- **Goal:** Make proposal and approval structures explicit enough for Hermes,
  OpenClaw, and broker APIs to share safely.
- **Requirements:** R1, R2, R3, R10
- **Files:** `src/vmga/proposals.py`, `src/vmga/approvals.py`,
  `schemas/vmga_proposal_v0.1.json`, `schemas/vmga_approval_v0.1.json`,
  `tests/test_vmga_contract.py`
- **Approach:** Add schema version fields and validation helpers. Approval
  binding should include action, actor, thread, message IDs, recipients,
  attachment IDs, content hash, expiration, proposal hash, and approver ID.
- **Test scenarios:**
  - Reordered recipients, message IDs, and attachment IDs do not change the
    canonical proposal hash.
  - Mutating action, content, recipients, message IDs, attachments, actor, or
    thread after approval invalidates execution.
  - Expired approvals and reused approvals deny with stable error codes.
  - Missing required production fields deny before policy evaluation.
- **Verification:** Schema validation tests plus approval replay/tamper tests.

### U3. Add Transactional Production State

- **Goal:** Provide durable state suitable for a broker without relying only on
  JSON files.
- **Requirements:** R3, R4, R5, R6
- **Files:** `src/vmga/state.py`, `src/vmga/sqlite_state.py`,
  `tests/test_vmga_state.py`
- **Approach:** Define a `VMGAStateStore` protocol and keep the JSON
  implementation as `JSONStateStore`. Add a SQLite implementation with
  transaction boundaries for proposal, approval, used-token, failed-attempt, and
  lockdown state.
- **Test scenarios:**
  - State persists pending proposals, approvals, used flags, denial counts, and
    lockdown after restart.
  - Concurrent execution attempts cannot consume the same approval twice.
  - Failed token attempts persist and rate-limit after restart.
  - Corrupted or unavailable production state fails closed.
- **Verification:** Shared state behavior suite against JSON and SQLite stores.

### U4. Build Evidence Ledger And Verifier

- **Goal:** Make VMGA evidence independently checkable.
- **Requirements:** R4, R10, R11
- **Files:** `src/vmga/evidence.py`, `src/vmga/ledger.py`,
  `scripts/verify_vmga_evidence.py`, `tests/test_vmga_evidence.py`,
  `docs/evidence.md`
- **Approach:** Add event builders for proposal received, validation passed or
  failed, policy decision, approval requested, approval verified, execution
  attempted, execution succeeded, execution denied, lockdown, and reset. Add a
  verifier that checks required event sequences and never requires raw secrets.
- **Test scenarios:**
  - Review-required proposal emits proposal, validation, policy, and
    approval-request events.
  - Approved execution emits approval verification, execution attempt, and
    execution result events.
  - Denials include machine-readable `error_code` and `rule_id`.
  - Ledger write failure denies kinetic actions.
  - Verifier catches missing approval evidence before execution evidence.
- **Verification:** `python3 scripts/verify_vmga_evidence.py <fixture-dir>` plus
  evidence unit tests.

### U5. Add Broker API Boundary

- **Goal:** Provide the runtime surface Hermes/OpenClaw can call without
  importing the entire adapter into the agent process.
- **Requirements:** R5, R6, R7, R8, R9
- **Files:** `src/vmga/broker.py`, `src/vmga/api.py`,
  `examples/broker_config.yaml`, `tests/test_vmga_broker.py`
- **Approach:** Start with an in-process service object and a minimal local HTTP
  server option. Endpoints should cover health, propose, approve callback or
  approval import, execute approved, and evidence status. Auth can start as a
  local bearer token with strict docs; production external auth remains a
  deployment concern.
- **Test scenarios:**
  - Broker health fails when policy, state, evidence, or executor dependencies
    are unavailable.
  - Proposal endpoint rejects malformed input and never performs side effects.
  - Kinetic execution endpoint requires valid approval binding.
  - Broker responses never include approval verifier secrets or Gmail tokens.
- **Verification:** Broker unit tests with fake executor and fake state.

### U6. Implement Gmail Backend Abstraction

- **Goal:** Decouple VMGA from any one Gmail implementation while keeping all
  side effects behind the execution gate.
- **Requirements:** R6, R9, R12
- **Files:** `src/vmga/executor.py`, `src/vmga/backends/`,
  `src/vmga/backends/fake_gmail.py`, `src/vmga/backends/gogcli.py`,
  `docs/gmail_backend_options.md`, `tests/test_vmga_executor.py`
- **Approach:** Add a backend protocol for read, search, create draft, send,
  archive, label, delete, and attachment download. Ship a fake backend first.
  Add `gogcli` as an optional backend only behind VMGA. Document `gws` as a
  high-power backend/reference that must not be agent-exposed.
- **Test scenarios:**
  - Fake backend records exactly which side effect would occur.
  - Executor denies side effects before backend call when approval is missing or
    binding mismatches.
  - `gogcli` command construction never exposes shell interpolation.
  - Backend errors produce evidence and do not mark approval used if no side
    effect occurred.
- **Verification:** Executor tests with fake backend and command-construction
  tests for optional CLI backend.

### U7. Ship Hermes Plugin Skeleton

- **Goal:** Make Hermes users able to call VMGA through native shell-free tools.
- **Requirements:** R7, R9, R12
- **Files:** `integrations/hermes/plugin.yaml`,
  `integrations/hermes/__init__.py`, `integrations/hermes/schemas.py`,
  `integrations/hermes/tools.py`, `integrations/hermes/skills/vmga-mail/SKILL.md`,
  `tests/test_hermes_plugin.py`, `docs/hermes_integration.md`
- **Approach:** Follow the Hermes plugin layout exactly. Tool handlers return
  JSON strings and call the VMGA broker. Kinetic tools return proposals, denials,
  or approval-required responses; they do not call Gmail directly.
- **Test scenarios:**
  - `plugin.yaml` declares only VMGA tool names.
  - Tool handlers return JSON strings on success and error.
  - `mail_send` and `mail_create_draft` create proposals, not Gmail side
    effects.
  - Missing broker or unhealthy VMGA returns fail-closed JSON.
  - Plugin does not use `ctx.dispatch_tool()` for terminal, browser, MCP, or
    native Gmail tools.
- **Verification:** Import/handler tests plus a static fixture check for the
  manifest and schemas.

### U8. Ship OpenClaw Integration Artifacts

- **Goal:** Make OpenClaw users able to wire VMGA through an explicit gateway or
  plugin boundary with bypass evidence.
- **Requirements:** R8, R9, R10, R11
- **Files:** `integrations/openclaw/openclaw.plugin.json`,
  `integrations/openclaw/profile_adapter.py`,
  `examples/openclaw_gateway_vmga.yaml`, `tests/test_openclaw_integration.py`,
  `docs/openclaw_integration.md`
- **Approach:** Provide an example plugin/gateway config that routes Gmail
  actions to the VMGA broker and denies direct Workspace paths. Include sample
  evidence checks for `/tools/invoke`, sandbox explain, secrets audit, operator
  scope posture, and paired node command surface.
- **Test scenarios:**
  - Manifest hash can be computed and included in release evidence.
  - Example config does not expose direct `gws`, `gog`, native Gmail, shell, or
    browser write paths to mailbox-capable agents.
  - OpenClaw request metadata maps into VMGA actor/session/proposal metadata.
  - Missing VMGA broker denies tool execution.
- **Verification:** Static config tests and adapter mapping tests.

### U9. Add Deployment Evidence Automation

- **Goal:** Turn release/checklist docs into reproducible commands.
- **Requirements:** R10, R11, R12
- **Files:** `scripts/vmga_release_check.py`, `scripts/build_vmga_evidence.py`,
  `docs/release_checklist.md`, `docs/deployment_runbook.md`,
  `tests/test_release_checks.py`
- **Approach:** Add a script that verifies package metadata, policy fixtures,
  schema files, safe examples, evidence fixtures, docs claim hygiene, and
  integration artifact presence. It should optionally ingest external command
  outputs from Hermes/OpenClaw deployments rather than requiring those tools
  locally.
- **Test scenarios:**
  - Script fails when example files contain fake-looking but real-risk token
    patterns.
  - Script fails when docs claim hard enforcement without deployment
    preconditions.
  - Script validates all policy YAML files load successfully.
  - Script confirms release evidence has Hermes/OpenClaw checklist slots.
- **Verification:** `python3 scripts/vmga_release_check.py --offline`.

### U10. Package, CI, And Public Examples

- **Goal:** Make the repo installable, testable, and understandable for outside
  users.
- **Requirements:** R5, R11, R12
- **Files:** `pyproject.toml`, `.github/workflows/ci.yml`,
  `.github/workflows/codeql.yml`, `examples/`, `README.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`
- **Approach:** Add package extras for `dev`, `broker`, `sqlite`, and optional
  backend integrations. Add example configs for advisory local mode, Hermes
  broker mode, and OpenClaw broker mode. Keep default examples fake and strict.
- **Test scenarios:**
  - `pip install -e ".[dev]"` works in a clean venv.
  - CI runs compileall, tests, policy validation, and release check.
  - Example configs parse and point at fake or placeholder values only.
  - README quickstart works without real Gmail credentials.
- **Verification:** Full CI plus local release check.

### U11. First Real Deployment Dry Run

- **Goal:** Prove the design against a non-production mailbox or fake backend
  before public release.
- **Requirements:** R4, R6, R7, R8, R9, R10
- **Files:** `artifacts/` or ignored local evidence output,
  `docs/dsovs_readiness.md`, `docs/release_checklist.md`
- **Approach:** Run VMGA in broker mode with fake backend first, then a test
  Gmail backend if available. Exercise read, draft proposal, approval, approved
  execution, denied send, tampered proposal, expired approval, bypass denial, and
  lockdown/reset. For Hermes/OpenClaw, capture deployment evidence when the
  runtimes are available.
- **Test scenarios:**
  - Fake backend dry run produces complete evidence.
  - Hermes plugin can submit proposals without Gmail credentials in the agent
    process.
  - OpenClaw example can demonstrate denied non-VMGA direct write path.
  - Evidence verifier passes on the dry-run bundle.
- **Verification:** Evidence bundle plus release checklist signoff.

## Sequencing

1. **Core contract pass:** U1 and U2.
2. **State/evidence pass:** U3 and U4.
3. **Broker/executor pass:** U5 and U6.
4. **Integration pass:** U7 and U8.
5. **Release machinery pass:** U9 and U10.
6. **Dry-run validation:** U11.

This order avoids building flashy integrations on top of unstable core binding
semantics.

## External Source Decisions To Preserve

- `orlyjamie/hardmail`: borrow shell-free Hermes mail ergonomics, not self-gated
  send approval.
- `openclaw/gogcli`: preferred optional CLI backend reference because of safety
  profiles, no-send support, and read-only MCP posture.
- `googleworkspace/cli`: useful reference for auth and Workspace breadth, but
  direct `gws` in an agent runtime is a bypass.
- OpenClaw docs: SecretRefs, sandboxing, fs-safe, pairing, operator scopes,
  trusted-proxy auth, `/tools/invoke`, and approvals are controls requiring
  deployment evidence, not VMGA enforcement by themselves.
- Hermes docs: plugin handlers, Docker/runtime isolation, Tool Gateway,
  credential pools, MCP env filtering, session storage, hooks, and CLI extension
  surfaces are relevant bypass and packaging inputs.
- OWASP DSOVS: use as readiness/evidence language, not as certification.

## Risks

- **False production confidence:** Mitigate with advisory-versus-hard-enforced
  labels and release checks for claim hygiene.
- **Adapter bypasses:** Mitigate with explicit Hermes/OpenClaw bypass tests,
  docs, and deployment evidence slots.
- **Approval replay or mutation:** Mitigate with expanded binding and
  transactional state.
- **Backend shell injection:** Mitigate by starting with fake backend and using
  structured subprocess invocation for optional CLI backends.
- **Integration drift:** Mitigate by keeping Hermes/OpenClaw integration tests
  mostly static/contract-based and documenting source versions reviewed.
- **Evidence gaps:** Mitigate with a verifier before public release.

## Definition Of Done

- All tests pass locally and in CI.
- VMGA core modules are split and compatibility exports remain stable.
- Proposal, approval, state, executor, and evidence contracts are versioned.
- Broker mode exists and can run against a fake backend.
- Hermes plugin skeleton can submit proposals through the broker.
- OpenClaw example artifacts map gateway/plugin calls to VMGA proposals.
- Release check passes without real credentials.
- Dry-run evidence bundle verifies.
- README and docs make the advisory/hard-enforced boundary impossible to miss.
