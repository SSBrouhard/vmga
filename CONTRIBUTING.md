# Contributing

VMGA changes should preserve the governing invariant:

> The agent may reason about email, but it may not grant itself mailbox
> authority.

Before opening a pull request:

- Keep changes scoped and explain any trust-boundary impact.
- Add or update tests for proposal validation, approval binding, execution
  gating, policy decisions, and evidence events.
- Do not commit secrets, OAuth client files, tokens, mailbox exports, or local
  VMGA state.
- Keep claims narrow. Avoid saying VMGA prevents prompt injection, provides DLP,
  certifies a deployment, or secures a host runtime.

Run:

```bash
python3 -m pip install -e ".[dev]"
pytest -q
```
