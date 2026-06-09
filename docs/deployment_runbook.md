# VMGA Deployment Runbook

This runbook describes the minimum deployment posture needed before VMGA can be
described as a hard Gmail governance boundary.

## Required Preconditions

1. The agent process cannot read Gmail OAuth tokens, approval verifier secrets,
   VMGA policy files, or executor credentials.
2. The agent cannot call Gmail write-capable APIs outside VMGA.
3. Approval happens through a channel the agent cannot spoof or operate.
4. VMGA state and evidence paths are not writable by the agent.
5. Kinetic actions fail closed when policy, state, approval, or evidence writes
   are unavailable.

## Advisory Mode

If VMGA runs in the same authority context as the agent, or if the agent can read
tokens and policy files, describe the deployment as advisory governance only.

## Evidence To Collect

- Service identity and filesystem permission output.
- Network egress rules showing direct Gmail write paths are unavailable to the
  agent.
- Policy file hash and deployment config hash.
- Sample ledger entries for allow, deny, review-required, approval, execution,
  lockdown, and reset.
