# Hermes Integration Notes

VMGA's Hermes integration should provide shell-free email tools inspired by
`hardmail`, while routing kinetic actions through VMGA's proposal and approval
contract.

## Target Tool Surface

- `mail_search`: read-only search.
- `mail_get`: read-only message retrieval.
- `mail_get_attachment`: governed attachment retrieval.
- `mail_create_draft`: proposal-backed draft creation.
- `mail_send`: proposal-backed send request, denied or held unless policy and
  approval permit execution.

## Important Difference From hardmail

`hardmail` self-gates `mail_send` inside the plugin. VMGA should not use
self-gating for production claims. VMGA approval must be out-of-band and bound to
the exact proposal hash.

## Toolset Scoping

Hermes deployments should scope VMGA mail tools only to platforms that need
email access and should avoid granting `terminal`, generic browser, or generic
web tools to the same untrusted mail-reading surface.
