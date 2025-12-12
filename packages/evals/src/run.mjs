/**
 * Deterministic citation checks for the local Signal Desk review artifact.
 */
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "../../..");
const reviewPath = join(root, "content/artifacts/signal-desk/latest-review.json");
const legacyPath = join(root, "content/artifacts/signal-desk/latest-issue.json");
const path = existsSync(reviewPath) ? reviewPath : legacyPath;
const issue = JSON.parse(readFileSync(path, "utf8"));

if (issue.delivery && issue.delivery !== "local-only") {
  console.error("Signal Desk must be local-only (no email delivery).");
  process.exit(1);
}
if (issue.stats?.emailed === true) {
  console.error("Signal Desk must never email.");
  process.exit(1);
}

let citations = 0;
let unsupported = 0;
for (const section of issue.sections) {
  if (section.heading === "Watchlist") continue;
  for (const p of section.paragraphs) {
    if (!p.citations?.length) unsupported += 1;
    else citations += 1;
  }
}

const citationRate = citations / Math.max(1, citations + unsupported);
const pass = citationRate >= 0.95;

console.log(
  JSON.stringify(
    {
      suite: "signal-desk-local-review",
      delivery: issue.delivery ?? "local-only",
      citationRate,
      claimsDropped: issue.stats?.claims_dropped ?? issue.cost?.claims_dropped ?? 0,
      pass,
    },
    null,
    2,
  ),
);

if (!pass) process.exit(1);
