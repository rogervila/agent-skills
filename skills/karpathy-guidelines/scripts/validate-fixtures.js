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
  "clarification-before-assumption",
  "surface-tradeoffs",
  "pushback-unnecessary-complexity",
  "simple-over-bloated",
  "avoid-unrelated-edits",
  "preserve-existing-style",
  "success-criteria-for-vague-task",
  "verification-before-completion",
  "cleanup-own-artifacts-only",
  "separate-unrelated-observations",
  "offline-karpathy-summary",
];

const requiredSkillTerms = [
  "Attributed Summary Of Karpathy's Observations",
  "Mission",
  "Activation Criteria",
  "Non-goals And Anti-patterns",
  "Required Inputs And Prerequisites",
  "Quick Start Workflow",
  "Mandatory Workflow Gates",
  "Gate 1: Understand Before Acting",
  "Gate 2: Define Success Criteria",
  "Gate 3: Prefer Simple, Correct Solutions",
  "Gate 4: Make Surgical Changes",
  "Gate 5: Implement Carefully",
  "Gate 6: Verify",
  "Gate 7: Self-review Before Final Response",
  "Clarification And Pushback Guidance",
  "Simplicity And Surgical Change Guidance",
  "Verification And Self-review Guidance",
  "Examples Of Good Behavior",
  "Examples Of Bad Behavior",
  "Final Response Expectations",
  "original summary",
  "without network access at runtime",
  "success criteria",
  "clarifying questions",
  "push back",
  "tradeoffs",
  "Would a senior engineer consider this overcomplicated?",
  "Every changed line should trace back to the user's request.",
  "Clean up only dead code",
  "Do not claim a task is complete only because code was edited.",
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
  assert(fixtures.skill === "karpathy-guidelines", "Fixture skill name mismatch");
  assert(Array.isArray(fixtures.fixtures), "fixtures must be an array");

  for (const term of requiredSkillTerms) {
    assert(skill.includes(term), `SKILL.md missing required Karpathy-guidelines term: ${term}`);
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
    assert(Array.isArray(fixture.covers), `${fixture.id} covers must be an array`);
    assert(Array.isArray(fixture.mustInclude), `${fixture.id} mustInclude must be an array`);
    assert(Array.isArray(fixture.mustAvoid), `${fixture.id} mustAvoid must be an array`);
    assert(fixture.covers.length > 0, `${fixture.id} must include at least one coverage tag`);
    assert(fixture.mustInclude.length > 0, `${fixture.id} must include at least one required behavior`);
    assert(fixture.mustAvoid.length > 0, `${fixture.id} must include at least one forbidden behavior`);
  }

  assert(
    skill.includes("This is an original summary") && skill.includes("not a copy"),
    "SKILL.md must state that the Karpathy summary is original and not copied",
  );
  assert(
    skill.includes("Third-party implementation reviewed for inspiration, not copied"),
    "SKILL.md must distinguish inspiration from copying the third-party skill",
  );

  console.log(`Validated ${fixtures.fixtures.length} Karpathy Guidelines behavior fixture(s).`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
