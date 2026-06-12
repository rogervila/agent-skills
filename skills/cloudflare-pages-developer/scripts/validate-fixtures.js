#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillDir = join(__dirname, "..");

const files = {
  skill: join(skillDir, "SKILL.md"),
  docs: join(skillDir, "references", "official-documentation.md"),
  fixtures: join(skillDir, "assets", "behavior-fixtures.json"),
};

const requiredCoverage = [
  "official-docs-links",
  "custom-headers",
  "redirects",
  "pages-functions",
  "pages-functions-vs-workers",
  "avoid-workers-only-deployment",
  "ambiguous-pages-workers-clarification",
  "pages-best-practices",
];

const requiredLinks = [
  "https://developers.cloudflare.com/llms.txt",
  "https://developers.cloudflare.com/pages/llms.txt",
  "https://developers.cloudflare.com/pages/",
  "https://developers.cloudflare.com/pages/get-started/git-integration/",
  "https://developers.cloudflare.com/pages/get-started/direct-upload/",
  "https://developers.cloudflare.com/pages/configuration/build-configuration/",
  "https://developers.cloudflare.com/pages/configuration/headers/",
  "https://developers.cloudflare.com/pages/configuration/redirects/",
  "https://developers.cloudflare.com/pages/functions/",
  "https://developers.cloudflare.com/pages/functions/routing/",
  "https://developers.cloudflare.com/pages/functions/wrangler-configuration/",
  "https://developers.cloudflare.com/pages/functions/bindings/",
  "https://developers.cloudflare.com/pages/functions/local-development/",
  "https://developers.cloudflare.com/workers/wrangler/commands/pages/",
];

const requiredSkillTerms = [
  "Cloudflare Pages",
  "Pages Functions",
  "standalone Workers",
  "_headers",
  "_redirects",
  "_routes.json",
  "pages_build_output_dir",
  "wrangler pages dev",
  "wrangler pages deploy",
  "Direct Upload",
  "Git integration",
  "production and preview",
  "compatibility_date",
  "compatibility_flags",
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function main() {
  const [skill, docs, fixturesRaw] = await Promise.all([
    readFile(files.skill, "utf8"),
    readFile(files.docs, "utf8"),
    readFile(files.fixtures, "utf8"),
  ]);

  const fixtures = JSON.parse(fixturesRaw);
  assert(fixtures.skill === "cloudflare-pages-developer", "Fixture skill name mismatch");
  assert(Array.isArray(fixtures.fixtures), "fixtures must be an array");

  const combinedDocs = `${skill}\n${docs}`;

  for (const link of requiredLinks) {
    assert(combinedDocs.includes(link), `Missing official docs link: ${link}`);
  }

  for (const term of requiredSkillTerms) {
    assert(skill.includes(term), `SKILL.md missing required Pages term: ${term}`);
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

  assert(
    skill.includes("Do not say Pages and Workers are the same product."),
    "SKILL.md must explicitly prevent Pages-vs-Workers equivalence",
  );
  assert(
    skill.includes("Do not recommend Workers-only Wrangler configuration keys"),
    "SKILL.md must warn against Workers-only Pages config advice",
  );

  console.log(`Validated ${fixtures.fixtures.length} Cloudflare Pages behavior fixture(s).`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
