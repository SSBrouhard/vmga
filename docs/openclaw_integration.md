# OpenClaw Integration Notes

VMGA should integrate with OpenClaw through an explicit plugin/gateway boundary.

OpenClaw's public security model is a personal-assistant trust model: one
trusted operator boundary per gateway, with separate gateways, OS users, or
hosts for materially different trust boundaries. VMGA must preserve that
assumption. If multiple untrusted users can trigger the same tool-enabled agent,
they share that agent's delegated mailbox authority unless the deployment splits
the runtime boundary.

The OpenClaw path must:

- Register VMGA as a plugin with explicit enablement.
- Map Gmail actions into structured VMGA proposals.
- Preserve `plugin_id`, `tool_id`, `actor_id`, and proposal metadata in evidence.
- Keep Gmail credentials and approval verifier secrets outside the agent process.
- Document that OpenClaw core internals are outside VMGA's enforcement claim.
- Treat OpenClaw `sessionKey` values and routing labels as context selectors, not
  as VMGA authorization boundaries.
- Require deployment evidence that direct Gmail and Google Workspace write paths
  are unavailable to the agent outside VMGA.
- Run `openclaw security audit --deep` before and after changing gateway bind,
  channel exposure, tool profiles, plugin enablement, or sandbox policy.

See `docs/deployment_runbook.md` for bypass-closure requirements.

## Recommended OpenClaw Posture

Start with the narrowest exposure pattern that supports the workflow:

- Keep the gateway loopback-only unless remote access is required.
- Use token/password or trusted-proxy authentication when the gateway is
  reachable off-host.
- Prefer pairing or strict sender allowlists for messaging channels.
- Use `session.dmScope: "per-channel-peer"` when more than one person can DM the
  bot.
- Disable host exec and elevated tools for any agent reachable from non-local
  senders.
- Keep browser, canvas, node, cron, gateway, and session-spawn tools away from
  open or semi-open mailbox workflows.
- Keep bind mounts narrow and exclude home directories, credential directories,
  Docker sockets, and system paths.

For company-shared workflows, use a dedicated runtime identity: a dedicated
machine, VM, container, or OS user; dedicated browser/profile/accounts; and no
personal Google account or password-manager state in that runtime.

## VMGA Bypass Controls For OpenClaw

The deployment is hard-enforced only if OpenClaw cannot reach Gmail side effects
without VMGA. Deny or remove these from the agent runtime:

- Direct `gws`, `gog`, `gmail`, or custom Workspace CLI execution unless the
  binary is a VMGA-owned broker path with isolated credentials.
- Environment credentials such as `GOOGLE_WORKSPACE_CLI_TOKEN`,
  `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE`, and `GOOGLE_APPLICATION_CREDENTIALS`.
- Credential directories such as `~/.config/gws`, `~/.config/gog`,
  `~/.hermes/google_token.json`, browser profile OAuth state, and OpenClaw
  agent auth profiles unless explicitly scoped for VMGA.
- Network egress from the agent sandbox directly to Gmail/Workspace APIs when
  write-capable credentials are present.
- Plugin-owned tools that expose Gmail writes without emitting VMGA proposals.

If any of those paths remain reachable, document the deployment as advisory
governance only.

## Exposure Validation

Before exposing an OpenClaw VMGA deployment:

1. Run `openclaw doctor`.
2. Run `openclaw security audit --deep`.
3. Prove an authorized sender can trigger a VMGA proposal.
4. Prove an unauthorized sender or browser session is denied.
5. Prove direct Gmail writes through non-VMGA tools fail.
6. Confirm approval-gated actions still require VMGA approval.
7. Confirm logs redact tokens and message secrets.
8. Record all accepted residual warnings.

VMGA release evidence should include the audit output, gateway configuration
hash, plugin manifest hash, policy hash, and representative VMGA evidence
entries for allow, review-required, deny, approval, execution, and lockdown.

## Formal-Model Alignment

OpenClaw's formal-verification documentation describes bounded TLA+/TLC models
for gateway exposure, node exec approvals, pairing caps, ingress gating, routing
isolation, and trace idempotency. VMGA should align with those modeled claims by
keeping approval tokens non-replayable, treating routing/session identifiers as
non-authoritative context, and recording stable trace identifiers across
proposal, approval, execution, and denial evidence.

Those models are useful regression references, but they are not proof that a
specific OpenClaw plus VMGA deployment is secure. VMGA's claim still depends on
the concrete deployment evidence above.

## Threat-Model Alignment

OpenClaw's MITRE ATLAS threat model frames the relevant boundaries as channel
access, session isolation, tool execution, external content, and supply chain.
For VMGA, map those boundaries this way:

- Channel access: who can trigger mailbox proposals.
- Session isolation: which actor/thread/message context is bound into the
  proposal and approval record.
- Tool execution: whether Gmail side effects can occur only through VMGA.
- External content: whether untrusted email content can influence action
  proposals without becoming authority.
- Supply chain: whether OpenClaw plugins, Hermes plugins, Workspace CLIs, and
  VMGA packages are pinned, reviewed, and explicitly enabled.

This keeps VMGA's claims bounded: VMGA governs Gmail actions at the mailbox
execution boundary; it does not make OpenClaw a hostile multi-tenant isolation
layer.

## References

- OpenClaw Gateway Security: https://docs.openclaw.ai/gateway/security
- OpenClaw Gateway Exposure Runbook:
  https://docs.openclaw.ai/gateway/security/exposure-runbook
- OpenClaw Formal Verification:
  https://docs.openclaw.ai/security/formal-verification
- OpenClaw MITRE ATLAS Threat Model:
  https://docs.openclaw.ai/security/THREAT-MODEL-ATLAS
