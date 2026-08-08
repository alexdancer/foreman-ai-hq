import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const MAX_OUTPUT_BYTES = 2 * 1024 * 1024;
const TERMINATION_GRACE_MS = 1_000;

function appendBounded(current, chunk) {
  const next = current + chunk;
  return next.length > MAX_OUTPUT_BYTES ? next.slice(-MAX_OUTPUT_BYTES) : next;
}

function diagnostics(message, stdout, stderr) {
  return new Error(`${message}\n--- Chrome stdout ---\n${stdout}\n--- Chrome stderr ---\n${stderr}`);
}

function waitForClose(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve();
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, timeoutMs);
    child.once("close", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

async function terminateProcessGroup(child) {
  if (child.exitCode !== null || child.signalCode !== null || !child.pid) return;
  const signalGroup = (signal) => {
    try {
      if (process.platform === "win32") child.kill(signal);
      else process.kill(-child.pid, signal);
    } catch (error) {
      if (error.code !== "ESRCH") throw error;
    }
  };
  signalGroup("SIGTERM");
  await waitForClose(child, TERMINATION_GRACE_MS);
  if (child.exitCode === null && child.signalCode === null) {
    signalGroup("SIGKILL");
    await waitForClose(child, TERMINATION_GRACE_MS);
  }
}

/**
 * Run a real headless Chrome contract until the page publishes a terminal DOM
 * marker, then reap only the Chrome process group this helper started.
 */
export function runRenderedBrowserContract({ browser, url, args = [], timeoutMs = 20_000 }) {
  const profile = mkdtempSync(join(tmpdir(), "foreman-browser-contract-"));
  return new Promise((resolve, reject) => {
    const child = spawn(browser, [
      "--headless",
      "--no-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      `--user-data-dir=${profile}`,
      ...args,
      "--dump-dom",
      url,
    ], {
      detached: process.platform !== "win32",
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    let timer;
    const finish = (error = null) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      terminateProcessGroup(child)
        .then(() => error ? reject(error) : resolve({ stdout, stderr }))
        .catch((terminationError) => reject(terminationError))
        .finally(() => rmSync(profile, { recursive: true, force: true }));
    };
    const fail = (message) => finish(diagnostics(message, stdout, stderr));
    const inspect = () => {
      if (stdout.includes('data-ledger-contract="failed"') || stdout.includes("data-contract-error=")) {
        fail("Rendered browser contract reported a failure marker.");
      } else if (stdout.includes('data-ledger-contract="passed"')) {
        finish();
      }
    };
    timer = setTimeout(() => fail(`Timed out after ${timeoutMs}ms before the rendered browser contract completed.`), timeoutMs);

    child.once("error", (error) => fail(`Could not start Chrome: ${error.message}`));
    child.stdout.on("data", (chunk) => {
      stdout = appendBounded(stdout, chunk.toString());
      inspect();
    });
    child.stderr.on("data", (chunk) => { stderr = appendBounded(stderr, chunk.toString()); });
    child.once("close", (code, signal) => {
      if (!settled) fail(`Chrome exited before the rendered browser contract completed (code ${code}, signal ${signal}).`);
    });
  });
}
