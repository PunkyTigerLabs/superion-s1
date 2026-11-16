#!/usr/bin/env node
/**
 * stdio entry point: `npx -y @punkytigerlabs/superion-s1-mcp`.
 * Reads SUPERION_API_KEY (and optionally SUPERION_BASE_URL, SUPERION_MODEL) from the environment.
 * stdout carries the MCP protocol; diagnostics go to stderr only.
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer, VERSION } from "./server.js";

async function main() {
  const server = createServer();
  await server.connect(new StdioServerTransport());
  if (!process.env.SUPERION_API_KEY) {
    console.error(
      `superion-s1-mcp ${VERSION}: SUPERION_API_KEY is not set; tools will return an error until it is. Free key: https://punkytigerlabs.com/s1/`,
    );
  }
}

main().catch((e) => {
  console.error("superion-s1-mcp failed to start:", e);
  process.exit(1);
});
