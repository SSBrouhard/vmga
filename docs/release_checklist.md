# VMGA Release Checklist

Before making VMGA public:

- Choose and add a real open-source license.
- Run the VMGA test suite.
- Run secrets scanning.
- Run SAST or document the static-analysis substitute.
- Review dependency and license posture.
- Verify docs do not claim prompt-injection prevention, DLP, host security,
  compliance certification, or hard isolation without deployment preconditions.
- Verify example policies use placeholder domains and strict defaults.
- Verify `SECURITY.md` has a monitored reporting path.
- Record DSOVS self-assessment evidence in `docs/dsovs_readiness.md`.
