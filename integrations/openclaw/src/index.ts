import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const DEFAULT_BROKER_URL = "http://127.0.0.1:8765";
const BROKER_ENDPOINT = "/v1/proposals";

const ConfigSchema = Type.Object(
  {
    broker_url: Type.Optional(Type.String({ description: "VMGA broker base URL." })),
    broker_token: Type.Optional(Type.String({ description: "Optional VMGA broker bearer token." })),
    broker_timeout_seconds: Type.Optional(Type.Number({ minimum: 1, maximum: 120 })),
  },
  { additionalProperties: false },
);

const CommonMailFields = {
  actor_id: Type.Optional(Type.String()),
  session_id: Type.Optional(Type.String()),
  thread_id: Type.Optional(Type.String()),
  message_ids: Type.Optional(Type.Array(Type.String())),
  message_id: Type.Optional(Type.String()),
  content: Type.Optional(Type.String()),
  subject: Type.Optional(Type.String()),
  recipients: Type.Optional(Type.Array(Type.String())),
  attachment_ids: Type.Optional(Type.Array(Type.String())),
  parameters: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
  justification: Type.Optional(Type.String()),
};

const MailSearchSchema = Type.Object(
  {
    ...CommonMailFields,
    query: Type.String({ description: "Gmail search query." }),
    max_results: Type.Optional(Type.Integer({ minimum: 1, maximum: 100 })),
  },
  { additionalProperties: false },
);

const MailGetSchema = Type.Object(
  {
    ...CommonMailFields,
    message_id: Type.String({ description: "Gmail message id." }),
  },
  { additionalProperties: false },
);

const MailTransformSchema = Type.Object(
  {
    ...CommonMailFields,
    message_id: Type.String({ description: "Gmail message id." }),
  },
  { additionalProperties: false },
);

const MailGetAttachmentSchema = Type.Object(
  {
    ...CommonMailFields,
    message_id: Type.String({ description: "Gmail message id." }),
    attachment_id: Type.String({ description: "Gmail attachment id." }),
  },
  { additionalProperties: false },
);

const MailCreateDraftSchema = Type.Object(
  {
    ...CommonMailFields,
    recipients: Type.Array(Type.String(), { minItems: 1 }),
    content: Type.String({ minLength: 1 }),
    subject: Type.Optional(Type.String()),
  },
  { additionalProperties: false },
);

const MailSendSchema = MailCreateDraftSchema;

const MailForwardSchema = MailCreateDraftSchema;

const MailMessageMutationSchema = Type.Object(
  {
    ...CommonMailFields,
  },
  { additionalProperties: false },
);

const MailApplyLabelSchema = Type.Object(
  {
    ...CommonMailFields,
    label: Type.String({ minLength: 1, description: "Allowed Gmail label to apply." }),
  },
  { additionalProperties: false },
);

const MailMoveSchema = Type.Object(
  {
    ...CommonMailFields,
    destination: Type.String({ minLength: 1, description: "Allowed mailbox destination." }),
  },
  { additionalProperties: false },
);

type JsonMap = Record<string, unknown>;

function asStringList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
  if (typeof value === "string") return [value];
  return [];
}

function asJsonMap(value: unknown): JsonMap {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as JsonMap;
  return {};
}

function extractPressureSignals(value: unknown): JsonMap[] {
  if (Array.isArray(value)) {
    return value.flatMap((item) => extractPressureSignals(item));
  }
  if (!value || typeof value !== "object") {
    return [];
  }

  const obj = value as JsonMap;
  if (obj.event_type === "vmga_pressure_signal") {
    return [obj];
  }

  const signals: JsonMap[] = [];
  for (const key of ["pressure_signals", "evidence", "evidence_events", "events"]) {
    const child = obj[key];
    if (Array.isArray(child) || (child && typeof child === "object")) {
      signals.push(...extractPressureSignals(child));
    }
  }
  return signals;
}

export function normalizeBrokerResult(responseOk: boolean, httpStatus: number, brokerResponse: unknown): JsonMap {
  const response = asJsonMap(brokerResponse);
  const brokerStatus = typeof response.status === "string" ? response.status.toUpperCase() : undefined;
  const deniedByBroker = brokerStatus === "DENY" || brokerStatus === "LOCKDOWN";
  return {
    status: responseOk && !deniedByBroker ? "OK" : "DENY",
    http_status: httpStatus,
    broker_status: brokerStatus,
    broker_response: brokerResponse,
    pressure_signals: extractPressureSignals(brokerResponse),
  };
}

export function buildPayload(toolName: string, action: string, params: JsonMap): JsonMap {
  const actorId = typeof params.actor_id === "string" && params.actor_id.trim() ? params.actor_id : "openclaw-operator";
  const parameters = asJsonMap(params.parameters);
  const payload: JsonMap = {
    action,
    actor_id: actorId,
    thread_id: params.thread_id,
    message_ids: asStringList(params.message_ids ?? params.message_id),
    content: params.content,
    subject: params.subject,
    recipients: asStringList(params.recipients),
    attachment_ids: asStringList(params.attachment_ids),
    parameters,
    justification: typeof params.justification === "string" ? params.justification : "",
    metadata: {
      source: "openclaw",
      tool_id: toolName,
      session_id: params.session_id,
    },
  };

  if (toolName === "mail_search") {
    payload.search_query = params.query;
    payload.max_results = params.max_results ?? 10;
  }
  if (toolName === "mail_get") {
    payload.message_id = params.message_id;
  }
  if (toolName === "mail_get_attachment") {
    payload.message_id = params.message_id;
    payload.attachment_ids = typeof params.attachment_id === "string" ? [params.attachment_id] : [];
  }
  if (toolName === "mail_apply_label" && typeof params.label === "string") {
    payload.parameters = { ...parameters, label: params.label };
  }
  if (toolName === "mail_move" && typeof params.destination === "string") {
    payload.parameters = { ...parameters, destination: params.destination };
  }
  return payload;
}

async function postToBroker(config: { broker_url?: string; broker_token?: string; broker_timeout_seconds?: number }, payload: JsonMap): Promise<JsonMap> {
  const brokerUrl = (config.broker_url || DEFAULT_BROKER_URL).replace(/\/+$/, "");
  const timeoutMs = Math.max(1, config.broker_timeout_seconds ?? 10) * 1000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" };
  if (config.broker_token) {
    headers.Authorization = `Bearer ${config.broker_token}`;
  }

  try {
    const response = await fetch(`${brokerUrl}${BROKER_ENDPOINT}`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const text = await response.text();
    let brokerResponse: unknown;
    try {
      brokerResponse = text ? JSON.parse(text) : null;
    } catch (error) {
      return {
        status: "DENY",
        error_code: "vmga_broker_bad_json",
        error: error instanceof Error ? error.message : String(error),
      };
    }
    return normalizeBrokerResult(response.ok, response.status, brokerResponse);
  } catch (error) {
    return {
      status: "DENY",
      error_code: "vmga_broker_unreachable",
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

function toolHandler(toolName: string, action: string) {
  return async (params: JsonMap, config: { broker_url?: string; broker_token?: string; broker_timeout_seconds?: number }) => {
    const payload = buildPayload(toolName, action, params);
    const result = await postToBroker(config, payload);
    return { tool: toolName, ...result };
  };
}

export default defineToolPlugin({
  id: "plugin.vmga",
  name: "VMGA Mail Governance",
  description: "Route OpenClaw mailbox tools through the VMGA broker.",
  configSchema: ConfigSchema,
  tools: (tool) => [
    tool({
      name: "mail_search",
      description: "Search Gmail through the VMGA broker.",
      parameters: MailSearchSchema,
      execute: toolHandler("mail_search", "read"),
    }),
    tool({
      name: "mail_get",
      description: "Read a Gmail message through the VMGA broker.",
      parameters: MailGetSchema,
      execute: toolHandler("mail_get", "read"),
    }),
    tool({
      name: "mail_summarize",
      description: "Propose/perform VMGA-governed message summarization.",
      parameters: MailTransformSchema,
      execute: toolHandler("mail_summarize", "summarize"),
    }),
    tool({
      name: "mail_classify",
      description: "Propose/perform VMGA-governed message classification.",
      parameters: MailTransformSchema,
      execute: toolHandler("mail_classify", "classify"),
    }),
    tool({
      name: "mail_extract_entities",
      description: "Extract message entities through the VMGA broker.",
      parameters: MailTransformSchema,
      execute: toolHandler("mail_extract_entities", "extract_entities"),
    }),
    tool({
      name: "mail_recommend_draft",
      description: "Generate a non-kinetic draft recommendation through VMGA.",
      parameters: MailTransformSchema,
      execute: toolHandler("mail_recommend_draft", "recommend_draft"),
    }),
    tool({
      name: "mail_get_attachment",
      description: "Request a Gmail attachment through the VMGA broker.",
      parameters: MailGetAttachmentSchema,
      execute: toolHandler("mail_get_attachment", "download_attachment"),
    }),
    tool({
      name: "mail_create_draft",
      description: "Propose draft creation through the VMGA broker.",
      parameters: MailCreateDraftSchema,
      execute: toolHandler("mail_create_draft", "create_draft"),
    }),
    tool({
      name: "mail_send",
      description: "Propose mail sending through the VMGA broker.",
      parameters: MailSendSchema,
      execute: toolHandler("mail_send", "send"),
    }),
    tool({
      name: "mail_forward",
      description: "Propose forwarding through the VMGA broker.",
      parameters: MailForwardSchema,
      execute: toolHandler("mail_forward", "forward"),
    }),
    tool({
      name: "mail_archive",
      description: "Propose archive through the VMGA broker.",
      parameters: MailMessageMutationSchema,
      execute: toolHandler("mail_archive", "archive"),
    }),
    tool({
      name: "mail_delete",
      description: "Propose deletion through the VMGA broker.",
      parameters: MailMessageMutationSchema,
      execute: toolHandler("mail_delete", "delete"),
    }),
    tool({
      name: "mail_apply_label",
      description: "Propose label application through the VMGA broker.",
      parameters: MailApplyLabelSchema,
      execute: toolHandler("mail_apply_label", "apply_label"),
    }),
    tool({
      name: "mail_mark_read",
      description: "Propose marking messages read through the VMGA broker.",
      parameters: MailMessageMutationSchema,
      execute: toolHandler("mail_mark_read", "mark_read"),
    }),
    tool({
      name: "mail_move",
      description: "Propose moving messages through the VMGA broker.",
      parameters: MailMoveSchema,
      execute: toolHandler("mail_move", "move"),
    }),
  ],
});
