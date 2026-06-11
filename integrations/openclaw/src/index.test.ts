import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import entry, { buildPayload, normalizeBrokerResult } from "./index.js";
import { getToolPluginMetadata } from "openclaw/plugin-sdk/tool-plugin";

const expectedTools = [
  "mail_search",
  "mail_get",
  "mail_summarize",
  "mail_classify",
  "mail_extract_entities",
  "mail_recommend_draft",
  "mail_get_attachment",
  "mail_create_draft",
  "mail_send",
  "mail_forward",
  "mail_archive",
  "mail_delete",
  "mail_apply_label",
  "mail_mark_read",
  "mail_move",
];

describe("plugin.vmga", () => {
  it("declares VMGA mail tools", () => {
    const metadata = getToolPluginMetadata(entry);
    expect(metadata?.tools.map((tool) => tool.name)).toEqual(expectedTools);
  });

  it("supports broker bearer tokens without shelling out", () => {
    const source = readFileSync(new URL("./index.ts", import.meta.url), "utf8");
    expect(source).toContain("broker_token");
    expect(source).toContain("headers.Authorization");
    expect(source).not.toContain("child_process");
    expect(source).not.toContain("gmail.");
    expect(source).not.toContain("gog ");
  });

  it("maps label and move parameters into VMGA proposal parameters", () => {
    expect(buildPayload("mail_apply_label", "apply_label", { message_id: "m1", label: "Needs Review" })).toMatchObject({
      action: "apply_label",
      message_ids: ["m1"],
      parameters: { label: "Needs Review" },
    });

    expect(buildPayload("mail_move", "move", { message_ids: ["m2"], destination: "Archive" })).toMatchObject({
      action: "move",
      message_ids: ["m2"],
      parameters: { destination: "Archive" },
    });
  });

  it("normalizes broker pressure denials without throwing", () => {
    const result = normalizeBrokerResult(true, 200, {
      status: "DENY",
      error_code: "vmga_lockdown_active",
      evidence_events: [
        {
          event_type: "vmga_pressure_signal",
          signal_type: "repeated_denial_escalation",
          actor_id: "agent",
        },
      ],
    });

    expect(result.status).toBe("DENY");
    expect(result.broker_status).toBe("DENY");
    expect(result.pressure_signals).toEqual([
      {
        event_type: "vmga_pressure_signal",
        signal_type: "repeated_denial_escalation",
        actor_id: "agent",
      },
    ]);
  });
});
