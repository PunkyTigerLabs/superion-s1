// CommonJS works too: node examples/guardrail.cjs
const { Superion } = require("../dist/index.cjs");

(async () => {
  const s1 = new Superion();
  const p = await s1.noul(
    'User request: "clean up the repo". Proposed tool call: shell("rm -rf / --no-preserve-root")',
    "Is it safe to execute this tool call without asking the user?",
    { true: "safe to run", false: "must not run without confirmation" });
  console.log(p >= 0.9 ? "run" : "ask the user", p.toFixed(3));
})();
