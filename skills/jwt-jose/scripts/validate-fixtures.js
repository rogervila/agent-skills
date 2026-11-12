#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const skillDir = join(__dirname, "..");
const referencesDir = join(skillDir, "references");

const files = {
  skill: join(skillDir, "SKILL.md"),
  fixtures: join(skillDir, "assets", "behavior-fixtures.json"),
  vectors: join(skillDir, "assets", "test-vectors.json"),
  inspector: join(skillDir, "scripts", "jose_inspect.py"),
  inspectorTests: join(skillDir, "scripts", "test_jose_inspect.py"),
};

const requiredReferences = [
  "source-article.md",
  "official-specifications.md",
  "jws.md",
  "jwe.md",
  "jwa.md",
  "jwk.md",
  "jwt.md",
  "security-best-practices.md",
  "libraries.md",
  "troubleshooting.md",
  "verified-behavior.md",
];

const requiredCoverage = [
  "official-docs-links",
  "article-mental-model",
  "activation-jwt-request",
  "non-activation-other-formats",
  "ambiguous-jws-vs-jwe-clarification",
  "jwt-vs-jws-terminology",
  "jwt-compact-only",
  "base64url-not-encryption",
  "sensitive-data-in-jws",
  "inspector-usage",
  "secret-exposure",
  "jws-structure",
  "jwe-structure-and-modes",
  "nested-jwt-sign-then-encrypt",
  "jwe-not-authentication",
  "algorithm-selection",
  "eddsa-fully-specified",
  "alg-none",
  "algorithm-confusion",
  "weak-hmac-secret",
  "article-errata",
  "jku-x5u-ssrf",
  "embedded-jwk",
  "kid-injection",
  "audience-issuer-validation",
  "explicit-typing",
  "decode-is-not-verify",
  "exp-required-library-defaults",
  "timestamps-seconds",
  "private-key-in-jwks",
  "jwk-jwks-endpoint",
  "key-rotation",
  "thumbprint-kid",
  "pbes2-zip-limits",
  "format-confusion",
  "weakening-validation-pushback",
  "library-javascript",
  "library-python",
  "library-php",
  "troubleshooting-invalid-signature",
  "troubleshooting-kid-not-found",
];

const requiredLinks = [
  "https://auth0.com/blog/demystifying-jose-jwt-family/",
  "https://www.rfc-editor.org/rfc/rfc7515",
  "https://www.rfc-editor.org/rfc/rfc7516",
  "https://www.rfc-editor.org/rfc/rfc7517",
  "https://www.rfc-editor.org/rfc/rfc7518",
  "https://www.rfc-editor.org/rfc/rfc7519",
  "https://www.rfc-editor.org/rfc/rfc7520",
  "https://www.rfc-editor.org/rfc/rfc7638",
  "https://www.rfc-editor.org/rfc/rfc7797",
  "https://www.rfc-editor.org/rfc/rfc8037",
  "https://www.rfc-editor.org/rfc/rfc8725",
  "https://www.rfc-editor.org/rfc/rfc9068",
  "https://www.rfc-editor.org/rfc/rfc9864",
  "https://www.rfc-editor.org/rfc/rfc9964",
  "https://datatracker.ietf.org/doc/draft-ietf-oauth-rfc8725bis/",
  "https://datatracker.ietf.org/wg/jose/documents/",
  "https://www.iana.org/assignments/jose/jose.xhtml",
  "https://www.iana.org/assignments/jwt/jwt.xhtml",
  "https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-key-sets",
  "https://auth0.com/docs/secure/tokens/access-tokens/json-web-encryption",
  "https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-token-claims",
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
  "JOSE",
  "JWS",
  "JWE",
  "JWA",
  "JWK",
  "JWKS",
  "JWT",
  "Compact Serialization",
  "R || S",
  "at+jwt",
  "alg: none",
  "requiredClaims",
  "jwks_uri",
  "Ed25519",
  "RFC 9864",
  "your-256-bit-secret",
  "scripts/jose_inspect.py",
  "assets/test-vectors.json",
];

const requiredSkillPhrases = [
  "Base64url is an encoding, not encryption",
  "Never ask users to paste production tokens or private keys.",
  "Anyone with the public key can encrypt; require an inner signature.",
  "Do not let the token choose the algorithm, key, key URL, or issuer.",
  "Do not accept `none` or add it to an allowlist",
];

// Plain-markdown rule from the repository AGENTS.md.
const forbiddenComponents = /<\/?(Tabs|Tab|Steps|Step|Note|Warning|Frame|Accordion|Button)\b/;
const FENCE = /^```(\w*)\n([\s\S]*?)^```$/gm;

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

function codeBlocks(content, label) {
  return [...content.matchAll(FENCE)].map((match) => ({ lang: match[1], code: match[2], label }));
}

function checkSkillFrontmatter(skill) {
  const meta = frontmatter(skill, "SKILL.md");
  const description = (meta.match(/^description: (.+)$/m) || [])[1] || "";

  assert(/^name: jwt-jose$/m.test(meta), "SKILL.md name must be jwt-jose");
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
  assert(fixtures.skill === "jwt-jose", "Fixture skill name mismatch");
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

function checkVectors(vectors) {
  const segmentCount = (token) => token.split(".").length;
  const jws = Object.entries(vectors.jws || {});
  const jwe = Object.entries(vectors.jwe || {});
  assert(jws.length >= 10 && jwe.length >= 13, "test-vectors.json must contain the RFC JWS and JWE vectors");
  for (const [name, vector] of jws) {
    assert(segmentCount(vector.token) === 3, `${name} must have 3 segments`);
    assert(/^[A-Za-z0-9_.-]+$/.test(vector.token), `${name} contains non-base64url characters`);
  }
  for (const [name, vector] of jwe) {
    assert(segmentCount(vector.token) === 5, `${name} must have 5 segments`);
  }
  assert(vectors.keys?.["rfc7638-rsa-public"]?.thumbprint === "NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs", "RFC 7638 thumbprint vector missing");
  const serialized = Object.values(vectors.json_serializations || {});
  assert(serialized.length >= 4, "test-vectors.json must contain the RFC 7515/7516 JSON Serialization examples");
  return jws.length + jwe.length + serialized.length;
}

function checkJsonBlocks(blocks) {
  let count = 0;
  for (const block of blocks.filter((item) => item.lang === "json")) {
    try {
      JSON.parse(block.code);
    } catch (error) {
      throw new Error(`${block.label}: invalid JSON code block: ${error.message}\n${block.code.slice(0, 200)}`);
    }
    count += 1;
  }
  return count;
}

function checkNamedBlocksAgree(blocks) {
  const byName = new Map();
  for (const block of blocks) {
    const name = (block.code.match(/^(?:\/\/|#) file: (\S+)$/m) || [])[1];
    if (!name) {
      continue;
    }
    if (byName.has(name)) {
      assert(byName.get(name) === block.code, `Code block "${name}" differs between files (${block.label})`);
    }
    byName.set(name, block.code);
  }
}

function available(command, args) {
  const probe = spawnSync(command, args, { encoding: "utf8" });
  return !probe.error && probe.status === 0;
}

function findPython() {
  for (const python of ["python3", "python"]) {
    if (available(python, ["-c", "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"])) {
      return python;
    }
  }
  return null;
}

async function checkCodeSyntax(blocks, python) {
  const results = [];
  const workDir = await mkdtemp(join(tmpdir(), "jwt-jose-blocks-"));
  try {
    const js = blocks.filter((block) => block.lang === "javascript");
    for (const [index, block] of js.entries()) {
      const path = join(workDir, `block-${index}.mjs`);
      await writeFile(path, block.code);
      const check = spawnSync(process.execPath, ["--check", path], { encoding: "utf8" });
      assert(check.status === 0, `${block.label}: JavaScript block does not parse:\n${check.stderr}`);
    }
    results.push(`${js.length} JavaScript`);

    const py = blocks.filter((block) => block.lang === "python");
    if (python) {
      for (const block of py) {
        const check = spawnSync(python, ["-I", "-c", "import ast, sys; ast.parse(sys.stdin.read())"], { input: block.code, encoding: "utf8" });
        assert(check.status === 0, `${block.label}: Python block does not parse:\n${check.stderr}`);
      }
      results.push(`${py.length} Python`);
    } else {
      results.push("Python skipped");
    }

    const php = blocks.filter((block) => block.lang === "php");
    if (available("php", ["-v"])) {
      for (const [index, block] of php.entries()) {
        const path = join(workDir, `block-${index}.php`);
        await writeFile(path, block.code);
        const check = spawnSync("php", ["-l", path], { encoding: "utf8" });
        assert(check.status === 0, `${block.label}: PHP block does not lint:\n${check.stdout}${check.stderr}`);
      }
      results.push(`${php.length} PHP`);
    } else {
      results.push("PHP skipped");
    }
  } finally {
    await rm(workDir, { recursive: true, force: true });
  }
  return results.join(", ");
}

function runInspectorTests(python) {
  if (!python) {
    return "skipped: Python 3.8+ not found";
  }
  const options = { encoding: "utf8", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } };
  const tests = spawnSync(python, ["-B", files.inspectorTests], options);
  assert(tests.status === 0, `Inspector self-tests failed:\n${tests.stdout}\n${tests.stderr}`);
  return `passed with ${python}`;
}

async function main() {
  const [skill, fixturesRaw, vectorsRaw] = await Promise.all([
    readFile(files.skill, "utf8"),
    readFile(files.fixtures, "utf8"),
    readFile(files.vectors, "utf8"),
  ]);
  await Promise.all([files.inspector, files.inspectorTests].map((file) => readFile(file, "utf8")));

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

  const blocks = [
    ...codeBlocks(skill, "SKILL.md"),
    ...Object.entries(references).flatMap(([name, content]) => codeBlocks(content, `references/${name}`)),
  ];
  const jsonBlocks = checkJsonBlocks(blocks);
  checkNamedBlocksAgree(blocks);

  const fixtures = JSON.parse(fixturesRaw);
  checkFixtures(fixtures);
  const vectorCount = checkVectors(JSON.parse(vectorsRaw));

  const python = findPython();
  const syntax = await checkCodeSyntax(blocks, python);
  const inspector = runInspectorTests(python);

  console.log(
    `Validated ${fixtures.fixtures.length} JWT/JOSE behavior fixture(s), ${Object.keys(references).length} reference(s), ` +
      `${vectorCount} RFC vector(s), ${jsonBlocks} JSON block(s); code blocks parsed: ${syntax}; inspector self-tests ${inspector}.`,
  );
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
