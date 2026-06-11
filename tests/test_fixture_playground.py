from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from vmga.redaction import SECRET_PATTERNS


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "vmga_fixture_playground.py"
FIXTURE_PATH = ROOT / "examples" / "fixtures" / "safe_mailbox.json"


def _load_playground():
    spec = importlib.util.spec_from_file_location("vmga_fixture_playground", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _line_has(lines: list[str], *parts: str) -> bool:
    return any(all(part in line for part in parts) for line in lines)


def test_fixture_mailbox_contains_only_placeholder_data():
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    data = json.loads(text)

    assert sorted(data) == ["fx_msg_001", "fx_msg_002"]
    assert "@gmail.com" not in text
    assert data["fx_msg_001"]["sender"] == "billing@example.com"
    assert data["fx_msg_002"]["sender"] == "ops@example.com"
    for name, pattern in SECRET_PATTERNS.items():
        assert not pattern.search(text), name


def test_fixture_playground_emits_expected_local_outcomes(tmp_path: Path):
    playground = _load_playground()
    lines: list[str] = []

    steps = playground.run_playground(tmp_path / "playground", force=True, emit=lines.append)

    step_names = [row["step"] for row in steps]
    assert "direct_execute_without_approval_denied" in step_names
    assert "replay_denied" in step_names
    assert "tamper_denied" in step_names
    assert _line_has(lines, 'step="replay_denied"', 'status="DENY"', 'error_code="vmga_approval_already_used"')
    assert _line_has(lines, 'event_type="vmga_pressure_signal"', 'signal_type="urgency_or_authority_pressure"')
    assert _line_has(lines, 'event_type="vmga_pressure_signal"', 'signal_type="repeated_denial_escalation"')
    assert _line_has(lines, 'event_type="vmga_pressure_signal"', 'signal_type="proposal_mutation_attempt"')

    transcript = tmp_path / "playground" / "playground_transcript.jsonl"
    evidence = tmp_path / "playground" / "evidence.jsonl"
    assert transcript.exists()
    assert evidence.exists()
    assert "vmga_approval_already_used" in transcript.read_text(encoding="utf-8")
    assert "vmga_pressure_signal" in evidence.read_text(encoding="utf-8")


def test_fixture_playground_stays_offline_and_fake_backend_only():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = [
        "urlopen",
        "requests",
        "subprocess",
        "gog",
        "gog-agent-safe",
        "googleapis",
        "gmail.com",
        "VMGA_BROKER_TOKEN",
    ]
    for token in forbidden:
        assert token not in source
    assert "FakeGmailBackend" in source
