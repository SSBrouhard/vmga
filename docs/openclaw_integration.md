# OpenClaw Integration Notes

VMGA should integrate with OpenClaw through an explicit plugin/gateway boundary.

The OpenClaw path must:

- Register VMGA as a plugin with explicit enablement.
- Map Gmail actions into structured VMGA proposals.
- Preserve `plugin_id`, `tool_id`, `actor_id`, and proposal metadata in evidence.
- Keep Gmail credentials and approval verifier secrets outside the agent process.
- Document that OpenClaw core internals are outside VMGA's enforcement claim.

See `docs/deployment_runbook.md` for bypass-closure requirements.
