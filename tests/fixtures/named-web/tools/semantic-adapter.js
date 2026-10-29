import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const [, , testFile, testId] = process.argv;
const fingerprint = createHash("sha256").update(readFileSync(testFile)).digest("hex");
process.stdout.write(JSON.stringify({
  schema: 1,
  test_id: testId,
  semantic_fingerprint: fingerprint,
  closure_complete: true,
  dependencies: [],
}));
