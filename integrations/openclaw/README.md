# VMGA OpenClaw Plugin

This OpenClaw tool plugin routes mailbox tool calls to the local VMGA broker.
It does not call Gmail, gog, Google Workspace, shell, browser, or terminal
tools directly.

Default broker URL: `http://127.0.0.1:8765`

Install locally during development:

```bash
cd integrations/openclaw
npm install
npm run plugin:validate
openclaw plugins install "$PWD" --link
```
