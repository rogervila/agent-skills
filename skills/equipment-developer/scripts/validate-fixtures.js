#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillDir = join(__dirname, "..");
const referencesDir = join(skillDir, "references");

const files = {
  skill: join(skillDir, "SKILL.md"),
  fixtures: join(skillDir, "assets", "behavior-fixtures.json"),
  doctor: join(skillDir, "scripts", "equipment_doctor.py"),
  doctorTests: join(skillDir, "scripts", "test_equipment_doctor.py"),
  exampleChecker: join(skillDir, "scripts", "check_code_examples.py"),
};

const requiredReferences = [
  "official-documentation.md",
  "project-setup.md",
  "cli-and-compilation.md",
  "dependency-injection.md",
  "configuration.md",
  "database.md",
  "logging.md",
  "queue.md",
  "scheduler.md",
  "storage.md",
  "testing.md",
  "fastapi.md",
  "mcp.md",
  "deployment.md",
  "maintaining-equipment.md",
  "typing.md",
  "verified-behavior.md",
];

const requiredCoverage = [
  "official-docs-links",
  "activation-equipment-project",
  "non-activation-generic-python",
  "ambiguous-equipment-clarification",
  "unittest-not-pytest",
  "test-discovery-command",
  "first-run-env-setup",
  "config-typing",
  "database-alembic-autogenerate",
  "queue-redis-worker",
  "redis-auth",
  "scheduler-config-injection",
  "storage-path-safety",
  "storage-driver-parity",
  "logging-channels",
  "test-isolation",
  "compile-safety",
  "equipment-new-safety",
  "maintainer-workflow",
  "fastapi-routes",
  "deployment-process-model",
  "typed-code",
  "job-import-cycle",
  "mcp-server-integration",
  "mcp-transport-safety",
];

const requiredLinks = [
  "https://equipment-python.vercel.app/llms.txt",
  "https://equipment-python.vercel.app/llms-full.txt",
  "https://equipment-python.vercel.app/docs/intro",
  "https://equipment-python.vercel.app/docs/getting-started/installation",
  "https://equipment-python.vercel.app/docs/getting-started/directory-structure",
  "https://equipment-python.vercel.app/docs/getting-started/common-workflows",
  "https://equipment-python.vercel.app/docs/features/dependency-injection",
  "https://equipment-python.vercel.app/docs/features/config",
  "https://equipment-python.vercel.app/docs/features/database",
  "https://equipment-python.vercel.app/docs/features/log",
  "https://equipment-python.vercel.app/docs/features/queue",
  "https://equipment-python.vercel.app/docs/features/scheduler",
  "https://equipment-python.vercel.app/docs/features/storage",
  "https://equipment-python.vercel.app/docs/features/tests",
  "https://equipment-python.vercel.app/docs/features/compilation",
  "https://equipment-python.vercel.app/docs/examples/fastapi",
  "https://equipment-python.vercel.app/docs/examples/mcp",
  "https://equipment-python.vercel.app/docs/reference/cli",
  "https://equipment-python.vercel.app/docs/reference/environment-variables",
  "https://equipment-python.vercel.app/docs/reference/maintenance",
  "https://github.com/rogervila/equipment",
  "https://pypi.org/project/equipment/",
];

const requiredSkillTerms = [
  "Activation Criteria",
  "Required Inputs And Prerequisites",
  "Quick Start Workflow",
  "Response Requirements",
  "Common Mistakes To Prevent",
  "Clarification Pattern",
  "Validation And Completion",
  "Failure And Escalation Behavior",
  "Output Expectations",
  "Reference Documentation",
  "Scripts And Assets",
  "class App(Equipment)",
  "app/__init__.py",
  "ThreadSafeSingleton",
  "python -m unittest",
  "discover -s tests -t .",
  "enterContext",
  "reset_singletons",
  "DB_CONNECTION=sqlite",
  "DB_DATABASE=database/database.sqlite",
  "target_metadata = Base.metadata",
  "with_scheduler=True",
  "REDIS_PASSWORD",
  ".required()",
  "references/verified-behavior.md",
  "references/mcp.md",
  "references/typing.md",
  "FastMCP",
  "scripts/equipment_doctor.py",
  "scripts/check_code_examples.py",
  "AbstractStorage",
  "AbstractLogger",
  "-> None",
  "--explicit-package-bases",
  "--follow-untyped-imports",
  "--disallow-untyped-defs",
];

const requiredSkillPhrases = [
  "Never introduce pytest unless the project already uses it.",
  "Never edit the installed `equipment` package.",
  "Do not run `equipment new` inside an existing project",
  "Fully type-annotate every function, method, and test you write",
  "import it inside the function",
];

// Plain-markdown rule from the repository CLAUDE.md.
const forbiddenComponents = /<\/?(Tabs|Tab|Steps|Step|Note|Warning|Frame|Accordion|Button)\b/;

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function frontmatter(content, label) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n/);
  assert(match, `${label} missing YAML frontmatter`);
  return match[1];
}

function checkCodeFences(content, label) {
  let open = false;
  content.split("\n").forEach((line, index) => {
    const fence = line.match(/^\s*```(.*)$/);
    if (!fence) {
      return;
    }
    if (!open) {
      assert(fence[1].trim().length > 0, `${label}:${index + 1} code fence missing language identifier`);
    }
    open = !open;
  });
  assert(!open, `${label} has an unclosed code fence`);
}

function checkSkillFrontmatter(skill) {
  const meta = frontmatter(skill, "SKILL.md");
  const description = (meta.match(/^description: (.+)$/m) || [])[1] || "";

  assert(/^name: equipment-developer$/m.test(meta), "SKILL.md name must be equipment-developer");
  assert(description.length >= 50 && description.length <= 1024, "SKILL.md description must be 50-1024 characters");
  assert(!/: /.test(description) && !/ #/.test(description), "SKILL.md description must be a plain YAML scalar");
  assert(/^license: MIT$/m.test(meta), "SKILL.md license must be MIT");
  for (const key of ["author", "repository", "version", "keywords"]) {
    assert(new RegExp(`^  ${key}: ".+"$`, "m").test(meta), `SKILL.md metadata.${key} must be a quoted string`);
  }

  const body = skill.slice(skill.indexOf("\n---\n", 4) + 5);
  assert(body.split("\n").length < 500, "SKILL.md body must stay under 500 lines");
}

async function checkReferences(skill) {
  const present = (await readdir(referencesDir)).filter((name) => name.endsWith(".md")).sort();

  for (const name of requiredReferences) {
    assert(present.includes(name), `Missing reference file: references/${name}`);
  }

  const contents = {};
  for (const name of present) {
    const label = `references/${name}`;
    const content = await readFile(join(referencesDir, name), "utf8");
    contents[name] = content;

    assert(skill.includes(label), `SKILL.md does not link ${label}`);

    const meta = frontmatter(content, label);
    assert(/^name: ".+"$/m.test(meta), `${label} frontmatter missing name`);
    assert(/^description: ".+"$/m.test(meta), `${label} frontmatter missing description`);
    assert(/^tags: \[.+\]$/m.test(meta), `${label} frontmatter missing tags`);
    assert(/^## Best Practices$/m.test(content), `${label} missing Best Practices section`);
    assert(!forbiddenComponents.test(content), `${label} contains JSX/HTML components`);
    checkCodeFences(content, label);
  }

  // Every references/*.md mentioned anywhere must exist.
  const mentioned = new Set();
  for (const text of [skill, ...Object.values(contents)]) {
    for (const match of text.matchAll(/references\/([a-z0-9-]+\.md)/g)) {
      mentioned.add(match[1]);
    }
  }
  for (const name of mentioned) {
    assert(present.includes(name), `Broken reference link: references/${name}`);
  }

  return contents;
}

function checkFixtures(fixtures) {
  assert(fixtures.skill === "equipment-developer", "Fixture skill name mismatch");
  assert(Array.isArray(fixtures.fixtures), "fixtures must be an array");

  const ids = new Set();
  for (const fixture of fixtures.fixtures) {
    assert(typeof fixture.id === "string" && fixture.id.length > 0, "Fixture missing id");
    assert(!ids.has(fixture.id), `Duplicate fixture id: ${fixture.id}`);
    ids.add(fixture.id);
    assert(Array.isArray(fixture.covers) && fixture.covers.length > 0, `${fixture.id} must cover a behavior`);
    assert(typeof fixture.prompt === "string" && fixture.prompt.length > 0, `${fixture.id} missing prompt`);
    assert(
      typeof fixture.expectedAnswerGuidance === "string" && fixture.expectedAnswerGuidance.length > 0,
      `${fixture.id} missing expectedAnswerGuidance`,
    );
    assert(Array.isArray(fixture.mustInclude) && fixture.mustInclude.length > 0, `${fixture.id} mustInclude must be a non-empty array`);
    assert(Array.isArray(fixture.mustAvoid) && fixture.mustAvoid.length > 0, `${fixture.id} mustAvoid must be a non-empty array`);
  }

  const covered = new Set(fixtures.fixtures.flatMap((fixture) => fixture.covers));
  for (const coverage of requiredCoverage) {
    assert(covered.has(coverage), `Missing behavior fixture coverage: ${coverage}`);
  }
}

function runPythonChecks() {
  for (const python of ["python3", "python"]) {
    const probe = spawnSync(python, ["-c", "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"]);
    if (probe.error || probe.status !== 0) {
      continue;
    }
    const options = { encoding: "utf8", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } };
    const examples = spawnSync(python, ["-B", files.exampleChecker, skillDir], options);
    assert(examples.status === 0, `Python examples are not valid and fully typed:\n${examples.stdout}\n${examples.stderr}`);
    const doctor = spawnSync(python, ["-B", files.doctorTests], options);
    assert(doctor.status === 0, `Doctor self-tests failed:\n${doctor.stdout}\n${doctor.stderr}`);
    return `ran with ${python}`;
  }
  return "skipped: Python 3.8+ not found";
}

async function main() {
  const [skill, fixturesRaw] = await Promise.all([
    readFile(files.skill, "utf8"),
    readFile(files.fixtures, "utf8"),
  ]);
  await Promise.all([files.doctor, files.doctorTests, files.exampleChecker].map((file) => readFile(file, "utf8")));

  checkSkillFrontmatter(skill);
  checkCodeFences(skill, "SKILL.md");

  for (const term of requiredSkillTerms) {
    assert(skill.includes(term), `SKILL.md missing required term: ${term}`);
  }
  for (const phrase of requiredSkillPhrases) {
    assert(skill.includes(phrase), `SKILL.md missing required guardrail: ${phrase}`);
  }

  const references = await checkReferences(skill);
  const combined = `${skill}\n${Object.values(references).join("\n")}`;
  for (const link of requiredLinks) {
    assert(combined.includes(link), `Missing official docs link: ${link}`);
  }

  checkFixtures(JSON.parse(fixturesRaw));

  const pythonStatus = runPythonChecks();
  console.log(
    `Validated ${JSON.parse(fixturesRaw).fixtures.length} Equipment Developer behavior fixture(s), ` +
      `${Object.keys(references).length} reference(s); typed-example check and doctor self-tests ${pythonStatus}.`,
  );
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
