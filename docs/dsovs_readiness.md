# DSOVS Readiness Mapping

VMGA uses the OWASP DevSecOps Verification Standard (DSOVS) as a
self-assessment lens for release readiness. This mapping is not OWASP
certification, endorsement, or compliance evidence by itself.

## Selected Controls

- `DSOVS-DES-002` Threat Modelling: VMGA must document trust domains,
  deployment preconditions, and bypass paths.
- `DSOVS-CODE-002` Hardcoded Secrets Detection: CI should scan for committed
  OAuth credentials, tokens, approval secrets, and private keys.
- `DSOVS-CODE-004` SAST: CI should run static analysis or a documented
  substitute before public release.
- `DSOVS-CODE-005` SCA: Dependencies should be scanned for known
  vulnerabilities.
- `DSOVS-CODE-006` Software License Compliance: Dependencies and borrowed
  prior art must have compatible licenses and attribution.
- `DSOVS-CODE-009` Secure Dependency Management: Dependency updates should be
  tracked and reviewed.
- `DSOVS-REL-003` Secret Management: Production docs must require Gmail tokens
  and approval secrets to live outside the agent authority domain.
- `DSOVS-REL-004` Secure Configuration: Example policies should be strict by
  default and reject unknown or ambiguous behavior.
- `DSOVS-REL-005` Security Policy Enforcement: VMGA must fail closed when policy,
  approval, state, or evidence requirements are missing.
- `DSOVS-REL-008` Secure Release Management: Releases should have a checklist,
  changelog, tests, and explicit claim boundaries.
- `DSOVS-OPR-004` Application Security Logging: VMGA evidence must be structured
  and must not log raw approval tokens or secrets.
- `DSOVS-OPR-005` Vulnerability Disclosure: Public release should include a
  monitored reporting path.
- `DSOVS-TEST-005` Security Test Coverage: Tests should map to proposal,
  approval, execution, policy, evidence, and lockdown requirements.

## Release Evidence

Before public release, collect:

- Test output for VMGA unit and contract tests.
- CI output for secrets scanning, static analysis, dependency review, and license
  review where configured.
- Documentation review showing production claims are bounded by deployment
  preconditions.
- Sample VMGA evidence ledger entries for allow, review-required, deny,
  approval, execution, lockdown, and reset paths.
