# Security Policy

VMGA is security-sensitive software, but this repository is not yet claiming a
stable production security boundary.

## Reporting

For now, report suspected vulnerabilities privately to the repository owner. Do
not include live Gmail tokens, approval secrets, or private mailbox contents in
reports.

## Scope

In scope:

- Proposal, approval, execution, and evidence integrity issues.
- Bypass paths in the VMGA control flow.
- Secret exposure in examples, packaging, or documentation.
- Misleading security claims in docs.

Out of scope:

- Host compromise.
- Prompt-injection prevention claims VMGA does not make.
- Gmail, Hermes, OpenClaw, or Google OAuth vulnerabilities outside the VMGA
  integration boundary.
