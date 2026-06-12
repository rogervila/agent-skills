#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillDir = join(__dirname, "..");

const files = {
  skill: join(skillDir, "SKILL.md"),
  fixtures: join(skillDir, "assets", "behavior-fixtures.json"),
};

const requiredCoverage = [
  "latency-bottleneck-activation",
  "memory-pressure-activation",
  "style-only-non-activation",
  "missing-baseline-escalation",
  "validation-requires-correctness-and-benchmark",
];

const requiredSkillTerms = [
  "Activation Criteria",
  "Required Inputs And Prerequisites",
  "Optimization Workflow",
  "Validation And Completion",
  "Failure And Escalation Behavior",
  "Output Expectations",
  "baseline",
  "profile",
  "benchmark",
  "hot path",
  "observable behavior",
  "Do not use this skill as the primary lens",
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function main() {
  const [skill, fixturesRaw] = await Promise.all([
    readFile(files.skill, "utf8"),
    readFile(files.fixtures, "utf8"),
  ]);

  const fixtures = JSON.parse(fixturesRaw);
  assert(fixtures.skill === "performance-optimization", "Fixture skill name mismatch");
  assert(Array.isArray(fixtures.fixtures), "fixtures must be an array");

  for (const term of requiredSkillTerms) {
    assert(skill.includes(term), `SKILL.md missing required performance term: ${term}`);
  }

  const covered = new Set(fixtures.fixtures.flatMap((fixture) => fixture.covers || []));
  for (const coverage of requiredCoverage) {
    assert(covered.has(coverage), `Missing behavior fixture coverage: ${coverage}`);
  }

  for (const fixture of fixtures.fixtures) {
    assert(typeof fixture.id === "string" && fixture.id.length > 0, "Fixture missing id");
    assert(typeof fixture.prompt === "string" && fixture.prompt.length > 0, `${fixture.id} missing prompt`);
    assert(
      typeof fixture.expectedAnswerGuidance === "string" && fixture.expectedAnswerGuidance.length > 0,
      `${fixture.id} missing expectedAnswerGuidance`,
    );
    assert(Array.isArray(fixture.mustInclude), `${fixture.id} mustInclude must be an array`);
    assert(Array.isArray(fixture.mustAvoid), `${fixture.id} mustAvoid must be an array`);
    assert(fixture.mustInclude.length > 0, `${fixture.id} must include at least one required behavior`);
    assert(fixture.mustAvoid.length > 0, `${fixture.id} must include at least one forbidden behavior`);
  }

  console.log(`Validated ${fixtures.fixtures.length} Performance Optimization behavior fixture(s).`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
