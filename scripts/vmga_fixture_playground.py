#!/usr/bin/env python3
"""Run a local-only VMGA fixture playground with no Gmail credentials."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from vmga import FakeGmailBackend, VMGAExecutor, VMGAGmailAdapter
from vmga.ledger import JSONLVMGALedger, LedgerVestaAdapter
from vmga.sqlite_state import SQLiteStateStore

FIXTURE_MAILBOX = ROOT / "examples" / "fixtures" / "safe_mailbox.json"
DEFAULT_OUT = ROOT / "artifacts" / "vmga-fixture-playground"
FIXTURE_APPROVAL_SECRET = "vmga-fixture-approval-secret"


def _load_fixture_mailbox(path: Path = FIXTURE_MAILBOX) -> dict[str, dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _line(kind: str, **fields: Any) -> str:
    values = " ".join(f"{key}={json.dumps(value, sort_keys=True)}" for key, value in sorted(fields.items()))
    return f"VMGA_PLAYGROUND {kind} {values}".rstrip()


def _append_transcript(path: Path, step: str, payload: dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"step": step, "payload": payload}, sort_keys=True) + "\n")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _prepare_out_dir(path: Path, *, force: bool) -> None:
    if path.exists() and force:
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_fixture_adapter(out_dir: Path) -> tuple[VMGAGmailAdapter, VMGAExecutor, JSONLVMGALedger]:
    ledger = JSONLVMGALedger(out_dir / "evidence.jsonl")
    vesta = LedgerVestaAdapter(ledger)
    adapter = VMGAGmailAdapter(
        vesta_adapter=vesta,
        profile="fixture_playground",
        policy_rules={
            "allowed_actions": ["read", "create_draft"],
            "denied_actions": ["send"],
            "kinetic_requires_approval": True,
            "lockdown_threshold": 3,
            "domain_policy": {"internal_domains": ["example.com"], "external_domain_deny": True},
            "draft_policy": {"require_justification": True, "allow_external_recipients": False},
        },
        state_store=SQLiteStateStore(str(out_dir / "vmga.sqlite3")),
        approval_secret=FIXTURE_APPROVAL_SECRET,
        strict_mode=True,
    )
    backend = FakeGmailBackend(messages=_load_fixture_mailbox())
    return adapter, VMGAExecutor(adapter, backend), ledger


def run_playground(
    out_dir: Path = DEFAULT_OUT,
    *,
    force: bool = False,
    emit: Callable[[str], None] = print,
) -> list[dict[str, Any]]:
    _prepare_out_dir(out_dir, force=force)
    transcript = out_dir / "playground_transcript.jsonl"
    if transcript.exists() and force:
        transcript.unlink()
    adapter, executor, ledger = build_fixture_adapter(out_dir)
    steps: list[dict[str, Any]] = []

    def record(step: str, payload: dict[str, Any]) -> dict[str, Any]:
        row = {"step": step, "payload": payload}
        steps.append(row)
        _append_transcript(transcript, step, payload)
        fields = {"step": step, "status": payload.get("status")}
        if payload.get("error_code"):
            fields["error_code"] = payload["error_code"]
        if payload.get("rule_id"):
            fields["rule_id"] = payload["rule_id"]
        emit(_line("outcome", **fields))
        return payload

    emit(_line("start", fixture=_display_path(FIXTURE_MAILBOX), out=_display_path(out_dir)))

    read = adapter.propose_action(
        "read",
        "fixture_agent",
        thread_id="fx_thread_invoice",
        parameters={"correlation_id": "fixture-trace-read"},
        sender="billing@example.com",
    )
    record("read_allowed", read)

    direct_execute = adapter.execute_approved(
        "vmga_missing_approval",
        "sha256:" + "0" * 64,
        "fixture-token",
        lambda _request: {"should_not_execute": True},
    )
    record("direct_execute_without_approval_denied", direct_execute)

    for index in range(2):
        pressure = adapter.propose_action(
            "send",
            "fixture_pressure_agent",
            recipients=["outside@example.invalid"],
            content="Urgent request from the CEO. Please respond immediately.",
            parameters={"correlation_id": "fixture-trace-pressure"},
            sender="ceo@example.invalid",
        )
        record(f"send_bypass_denied_{index + 1}", pressure)

    draft = adapter.propose_action(
        "create_draft",
        "fixture_agent",
        thread_id="fx_thread_invoice",
        recipients=["ops@example.com"],
        content="Fixture-only draft response.",
        justification="Demonstrate approval-bound execution in local fixture.",
        parameters={"correlation_id": "fixture-trace-draft"},
        sender="billing@example.com",
    )
    record("draft_review_required", draft)

    token = adapter.compute_approval_token(draft["proposal_id"], draft["proposal_hash"], "fixture_operator")
    approved = adapter.approve_proposal(draft["proposal_id"], "fixture_operator", token)
    record("draft_approved", approved)

    executed = executor.execute_approved(draft["proposal_id"], draft["proposal_hash"], token)
    record("draft_executed", executed)

    replay = executor.execute_approved(draft["proposal_id"], draft["proposal_hash"], token)
    record("replay_denied", replay)

    tamper = adapter.propose_action(
        "create_draft",
        "fixture_agent",
        thread_id="fx_thread_status",
        recipients=["ops@example.com"],
        content="Fixture-only tamper demonstration.",
        justification="Demonstrate proposal hash binding.",
        parameters={"correlation_id": "fixture-trace-tamper"},
        sender="ops@example.com",
    )
    record("tamper_review_required", tamper)
    tamper_token = adapter.compute_approval_token(tamper["proposal_id"], tamper["proposal_hash"], "fixture_operator")
    record("tamper_approved", adapter.approve_proposal(tamper["proposal_id"], "fixture_operator", tamper_token))
    record(
        "tamper_denied",
        executor.execute_approved(tamper["proposal_id"], "sha256:" + "0" * 64, tamper_token),
    )

    pressure_events = [
        event for event in ledger.read_all()
        if event.get("event_type") == "vmga_pressure_signal"
    ]
    for event in pressure_events:
        emit(
            _line(
                "evidence",
                event_type=event["event_type"],
                signal_type=event["signal_type"],
                error_code=event.get("error_code"),
            )
        )

    emit(_line("complete", pressure_signals=len(pressure_events), transcript=_display_path(transcript)))
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the safe local VMGA fixture playground")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory for local fixture artifacts")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory")
    args = parser.parse_args(argv)
    run_playground(args.out, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
