import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { runRenderedBrowserContract } from "./browser-contract.mjs";

const fakeBrowser = fileURLToPath(new URL("./fixtures/fake-browser.mjs", import.meta.url));

async function processDisappears(pid, timeoutMs = 1_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      process.kill(pid, 0);
    } catch (error) {
      if (error.code === "ESRCH") return true;
      throw error;
    }
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  return false;
}

test("rendered browser contract terminates and reaps its exact successful process group", {
  skip: process.platform === "win32",
}, async () => {
  const { stdout } = await runRenderedBrowserContract({
    browser: fakeBrowser,
    url: "fixture://success",
    timeoutMs: 2_000,
  });
  const grandchildPid = Number(stdout.match(/grandchild=(\d+)/)?.[1]);
  assert.ok(Number.isInteger(grandchildPid), "fake browser must report its child pid");
  assert.equal(await processDisappears(grandchildPid), true);
});

test("rendered browser contract captures output without exceeding its bound", async () => {
  const { stderr } = await runRenderedBrowserContract({
    browser: fakeBrowser,
    url: "fixture://bounded",
    timeoutMs: 2_000,
  });
  assert.equal(stderr.length, 2 * 1024 * 1024);
  assert.match(stderr, /^x+$/);
});

test("rendered browser contract rejects a failure marker even beside a passed marker", async () => {
  await assert.rejects(
    runRenderedBrowserContract({ browser: fakeBrowser, url: "fixture://failed", timeoutMs: 2_000 }),
    /reported a failure marker/,
  );
});

test("rendered browser contract times out before a marker with captured diagnostics", async () => {
  await assert.rejects(
    runRenderedBrowserContract({ browser: fakeBrowser, url: "fixture://timeout", timeoutMs: 50 }),
    (error) => {
      assert.match(error.message, /Timed out after 50ms/);
      assert.match(error.message, /pre-marker diagnostic/);
      return true;
    },
  );
});
