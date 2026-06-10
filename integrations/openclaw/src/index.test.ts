import { describe, expect, it } from "vitest";
import entry from "./index.js";
import { getToolPluginMetadata } from "openclaw/plugin-sdk/tool-plugin";

describe("plugin.vmga", () => {
  it("declares VMGA mail tools", () => {
    const metadata = getToolPluginMetadata(entry);
    expect(metadata?.tools.map((tool) => tool.name)).toEqual([
      "mail_search",
      "mail_get",
      "mail_get_attachment",
      "mail_create_draft",
      "mail_send",
    ]);
  });
});
