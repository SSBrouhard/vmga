"""OpenClaw profile adapter wiring to VMGA broker."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional
from urllib import error
from urllib import request as urllib_request


@dataclass(frozen=True)
class OpenClawRequest:
    tool_id: str
    payload: Mapping[str, Any]
    actor_id: str = "openclaw-operator"
    session_id: str = "openclaw-session"


BROKER_ENDPOINT = "/v1/proposals"

OPENCLAW_TOOL_MAP: Dict[str, str] = {
    "mail_search": "read",
    "mail_get": "read",
    "mail_summarize": "summarize",
    "mail_classify": "classify",
    "mail_extract_entities": "extract_entities",
    "mail_recommend_draft": "recommend_draft",
    "mail_get_attachment": "download_attachment",
    "mail_create_draft": "create_draft",
    "mail_send": "send",
    "mail_forward": "forward",
    "mail_archive": "archive",
    "mail_delete": "delete",
    "mail_apply_label": "apply_label",
    "mail_mark_read": "mark_read",
    "mail_move": "move",
}


DISALLOWED_TOOL_PREFIXES: List[str] = [
    "gmail",
    "gws",
    "gog",
    "workspace",
    "terminal",
    "browser",
    "node.",
]


def _coerce_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float)):
        return [str(value)]
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _is_disallowed_tool(tool_id: str) -> bool:
    tool_norm = tool_id.lower()
    return any(tool_norm == prefix or tool_norm.startswith(prefix) for prefix in DISALLOWED_TOOL_PREFIXES)


def _coerce_recipients(payload: Mapping[str, Any]) -> List[str]:
    return _coerce_string_list(payload.get("recipients"))


def _coerce_message_ids(payload: Mapping[str, Any]) -> List[str]:
    message_ids = _coerce_string_list(payload.get("message_ids"))
    if message_ids:
        return message_ids
    message_id = payload.get("message_id")
    if message_id is not None:
        return [str(message_id)]
    return []


def _coerce_parameters(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _extract_pressure_signals(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        if value.get("event_type") == "vmga_pressure_signal":
            return [dict(value)]

        signals: List[Dict[str, Any]] = []
        for key in ("pressure_signals", "evidence", "evidence_events", "events"):
            child = value.get(key)
            if isinstance(child, list):
                for item in child:
                    signals.extend(_extract_pressure_signals(item))
            elif isinstance(child, dict):
                signals.extend(_extract_pressure_signals(child))
        return signals

    if isinstance(value, list):
        signals = []
        for item in value:
            signals.extend(_extract_pressure_signals(item))
        return signals

    return []


def _adapter_success_status(broker_response: Any) -> str:
    if isinstance(broker_response, dict):
        broker_status = str(broker_response.get("status", "")).upper()
        if broker_status in {"DENY", "LOCKDOWN"}:
            return "DENY"
    return "OK"


class VMGAOpenClawProfileAdapter:
    """Minimal mapping adapter for OpenClaw tool requests into VMGA proposal calls."""

    def __init__(
        self,
        broker_url: str,
        *,
        timeout_seconds: float = 2.5,
        bearer_token: Optional[str] = None,
        extra_map: Optional[Mapping[str, str]] = None,
    ):
        self.broker_url = broker_url
        self.timeout_seconds = timeout_seconds
        self.bearer_token = bearer_token
        self.tool_map = dict(OPENCLAW_TOOL_MAP)
        if extra_map:
            for key, value in extra_map.items():
                if isinstance(key, str) and isinstance(value, str):
                    self.tool_map[key] = value

    def map_tool(self, tool_id: str) -> str:
        if tool_id in self.tool_map:
            return self.tool_map[tool_id]
        return "read"

    def build_broker_payload(self, request: OpenClawRequest) -> Dict[str, Any]:
        if _is_disallowed_tool(request.tool_id):
            raise ValueError(f"tool is denied by VMGA static policy: {request.tool_id}")

        action = self.map_tool(request.tool_id)
        payload = {
            "proposal_id": f"openclaw_{request.tool_id}_{request.session_id}",
            "action": action,
            "actor_id": request.actor_id,
            "session_id": request.session_id,
            "thread_id": request.payload.get("thread_id"),
            "message_ids": _coerce_message_ids(request.payload),
            "content": request.payload.get("content"),
            "subject": request.payload.get("subject"),
            "recipients": _coerce_recipients(request.payload),
            "attachment_ids": request.payload.get("attachment_ids", []),
            "parameters": _coerce_parameters(request.payload.get("parameters")),
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "source": "openclaw",
                "tool_id": request.tool_id,
            },
        }

        if request.tool_id == "mail_apply_label" and request.payload.get("label"):
            payload["parameters"] = {**payload["parameters"], "label": str(request.payload["label"])}
        if request.tool_id == "mail_move" and request.payload.get("destination"):
            payload["parameters"] = {**payload["parameters"], "destination": str(request.payload["destination"])}

        # Ensure deterministic JSON shapes for audit/evidence correlation.
        payload["message_ids"] = [str(value) for value in payload["message_ids"]]
        payload["attachment_ids"] = [str(value) for value in payload["attachment_ids"]]
        return payload

    def execute(self, request_obj: OpenClawRequest) -> Dict[str, Any]:
        try:
            payload = self.build_broker_payload(request_obj)
        except ValueError as exc:
            return {
                "status": "DENY",
                "tool": request_obj.tool_id,
                "error_code": "vmga_tool_denied",
                "error": str(exc),
            }

        try:
            request_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            if self.bearer_token:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
            req = urllib_request.Request(
                self.broker_url.rstrip("/") + BROKER_ENDPOINT,
                data=request_payload,
                method="POST",
                headers=headers,
            )
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_json = json.loads(response.read().decode("utf-8"))
            return {
                "status": _adapter_success_status(response_json),
                "tool": request_obj.tool_id,
                "broker_response": response_json,
                "pressure_signals": _extract_pressure_signals(response_json),
            }
        except error.URLError as exc:
            return {
                "status": "DENY",
                "tool": request_obj.tool_id,
                "error_code": "vmga_broker_unreachable",
                "error": str(exc),
            }
        except (TypeError, ValueError) as exc:
            return {
                "status": "DENY",
                "tool": request_obj.tool_id,
                "error_code": "vmga_broker_response_invalid",
                "error": str(exc),
            }
        except Exception as exc:
            return {
                "status": "DENY",
                "tool": request_obj.tool_id,
                "error_code": "vmga_adapter_failure",
                "error": str(exc),
            }
