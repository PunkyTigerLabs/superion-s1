// End-to-end over stdio: spawn the real binary, list tools, call one.
// Without a key (forced empty), the call must return the setup error; no network is used.
import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const bin = fileURLToPath(new URL("../dist/index.js", import.meta.url));

test("stdio: initialize, list tools and call one without a key", async () => {
  const env = { ...process.env, SUPERION_API_KEY: "" };
  const transport = new StdioClientTransport({ command: process.execPath, args: [bin], env, stderr: "pipe" });
  const client = new Client({ name: "stdio-test", version: "0.0.0" });
  await client.connect(transport);
  try {
    assert.equal(client.getServerVersion().name, "superion-s1");
    assert.match(client.getInstructions() ?? "", /calibrated/);
    const { tools } = await client.listTools();
    assert.deepEqual(tools.map((t) => t.name).sort(), ["check_action", "classify", "decide", "decide_yes_no", "score"]);
    const r = await client.callTool({ name: "decide_yes_no", arguments: { text: "hello", question: "Is this a greeting?" } });
    assert.equal(r.isError, true);
    assert.match(r.content[0].text, /SUPERION_API_KEY is not set/);
  } finally {
    await client.close();
  }
});
