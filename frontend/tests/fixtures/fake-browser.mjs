#!/usr/bin/env node
import { spawn } from "node:child_process";

const url = process.argv.at(-1);

if (url === "fixture://failed") {
  process.stdout.write('<main data-ledger-contract="passed" data-ledger-contract="failed"></main>');
  setInterval(() => {}, 1_000);
} else if (url === "fixture://timeout") {
  process.stderr.write("pre-marker diagnostic");
  setInterval(() => {}, 1_000);
} else if (url === "fixture://bounded") {
  process.stderr.write("x".repeat(3 * 1024 * 1024), () => {
    process.stdout.write('<main data-ledger-contract="passed"></main>');
  });
  setInterval(() => {}, 1_000);
} else {
  const grandchild = spawn(process.execPath, ["-e", "setInterval(() => {}, 1000)"], { stdio: "ignore" });
  process.stdout.write(`grandchild=${grandchild.pid}\n<main data-ledger-contract="passed"></main>`);
  setInterval(() => {}, 1_000);
}
