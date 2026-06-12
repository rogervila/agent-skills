---
name: "Official Cloudflare Pages Documentation"
description: "Curated official Cloudflare Pages documentation links and source-of-truth guidance for the Cloudflare Pages Developer skill."
tags: [cloudflare, pages, docs, llms, functions, wrangler, headers, redirects]
---

# Official Cloudflare Pages Documentation

Last checked: 2026-06-12.

Use Cloudflare's current documentation as the source of truth. Prefer linking to docs over repeating volatile details such as limits, framework preset outputs, binding support, pricing, and command flags.

## LLM Documentation Sources

| Source | URL | Use |
|---|---|---|
| Cloudflare docs directory | https://developers.cloudflare.com/llms.txt | Discover current Cloudflare product documentation indexes. |
| Cloudflare Pages LLM index | https://developers.cloudflare.com/pages/llms.txt | Discover current Pages Markdown docs by topic. |
| Cloudflare Pages full LLM source | https://developers.cloudflare.com/pages/llms-full.txt | Use when available and the consuming tool can handle a large combined docs file. |
| Cloudflare docs for agents | https://developers.cloudflare.com/docs-for-agents/ | Understand how Cloudflare expects agents to consume docs. |

Cloudflare's `llms.txt` files point to Markdown versions of documentation pages. If an agent needs a specific page as Markdown, use the Markdown link from the Pages LLM index or request the normal docs URL with `Accept: text/markdown` when supported.

## Core Pages Docs

| Topic | Official URL | Notes for agents |
|---|---|---|
| Pages overview | https://developers.cloudflare.com/pages/ | Start here for the current product description and deployment options. |
| Get started | https://developers.cloudflare.com/pages/get-started/ | Use for first-project workflows. |
| Git integration | https://developers.cloudflare.com/pages/get-started/git-integration/ | Use for GitHub/GitLab projects, automatic builds, production branch, and preview deployments. |
| Direct Upload | https://developers.cloudflare.com/pages/get-started/direct-upload/ | Use for prebuilt asset uploads through Wrangler or dashboard drag and drop. |
| C3 CLI | https://developers.cloudflare.com/pages/get-started/c3/ | Use for new projects scaffolded with Cloudflare's CLI. |
| Framework guides | https://developers.cloudflare.com/pages/framework-guides/ | Use for framework-specific Pages deployment advice. |

## Configuration And Static Assets

| Topic | Official URL | Notes for agents |
|---|---|---|
| Configuration index | https://developers.cloudflare.com/pages/configuration/ | Pages-specific configuration topics. |
| Build configuration | https://developers.cloudflare.com/pages/configuration/build-configuration/ | Build commands, build output directories, and framework presets. |
| Build image | https://developers.cloudflare.com/pages/configuration/build-image/ | Supported languages, tools, build system, and image behavior. |
| Preview deployments | https://developers.cloudflare.com/pages/configuration/preview-deployments/ | Preview URLs, branch aliases, Access protection, and preview indexing. |
| Serving Pages | https://developers.cloudflare.com/pages/configuration/serving-pages/ | Static asset route matching, SPA behavior, caching, default headers, and `404.html`. |
| Custom headers | https://developers.cloudflare.com/pages/configuration/headers/ | `_headers` syntax and static response behavior. |
| Redirects | https://developers.cloudflare.com/pages/configuration/redirects/ | `_redirects` syntax, limits, proxying behavior, and redirect/header order. |
| Limits | https://developers.cloudflare.com/pages/platform/limits/ | Current Pages limits for builds, files, headers, redirects, Functions, and projects. |
| Known issues | https://developers.cloudflare.com/pages/platform/known-issues/ | Current documented limitations. |

## Pages Functions Docs

| Topic | Official URL | Notes for agents |
|---|---|---|
| Functions overview | https://developers.cloudflare.com/pages/functions/ | Pages Functions run on the Workers runtime inside the Pages model. |
| Get started with Functions | https://developers.cloudflare.com/pages/functions/get-started/ | First Function workflow. |
| Routing | https://developers.cloudflare.com/pages/functions/routing/ | `/functions` file-based routing, dynamic segments, `_routes.json`, and fallback behavior. |
| API reference | https://developers.cloudflare.com/pages/functions/api-reference/ | `EventContext`, `context.env`, `context.params`, `context.data`, and handler signatures. |
| Middleware | https://developers.cloudflare.com/pages/functions/middleware/ | Shared logic in Pages Functions. |
| Wrangler configuration | https://developers.cloudflare.com/pages/functions/wrangler-configuration/ | Pages-specific Wrangler config, `pages_build_output_dir`, environments, bindings, and differences from Workers config. |
| Local development | https://developers.cloudflare.com/pages/functions/local-development/ | `wrangler pages dev` workflow for static assets and Functions. |
| Bindings | https://developers.cloudflare.com/pages/functions/bindings/ | Pages-supported bindings and environment variables. |
| TypeScript | https://developers.cloudflare.com/pages/functions/typescript/ | Type generation and TypeScript authoring for Pages Functions. |
| Advanced mode | https://developers.cloudflare.com/pages/functions/advanced-mode/ | `_worker.js` advanced mode when a project needs it. |
| Debugging and logging | https://developers.cloudflare.com/pages/functions/debugging-and-logging/ | Logs and troubleshooting for Pages Functions. |

## Wrangler Docs

| Topic | Official URL | Notes for agents |
|---|---|---|
| Wrangler Pages commands | https://developers.cloudflare.com/workers/wrangler/commands/pages/ | Pages-specific commands such as `pages dev`, `pages deploy`, `pages project create`, and `pages deployment list`. |
| Wrangler install/update | https://developers.cloudflare.com/workers/wrangler/install-and-update/ | Current install and update instructions. |
| Workers Wrangler configuration | https://developers.cloudflare.com/workers/wrangler/configuration/ | Use only for shared config concepts or fields explicitly valid for Pages. |

## Pages Vs Workers Source-Of-Truth Notes

- Pages Functions use Workers runtime APIs, compatibility dates, and compatibility flags where documented by Cloudflare.
- Pages Functions still use Pages routing, Pages deployment, Pages project configuration, and Pages static asset behavior.
- A Pages Wrangler config is not identical to a standalone Workers config. `pages_build_output_dir` is Pages-specific, while Workers-only fields such as `main` do not apply to Pages Functions configuration.
- Pages static `_headers` and `_redirects` do not apply to responses generated by Pages Functions. Set headers and redirects in Function code for Function responses, or exclude routes from Functions when static behavior should apply.
- Pages-supported bindings are a documented subset. Check the Pages Functions bindings docs before recommending a binding, trigger, or local-development flag.

## Best Practices

- Link the exact Cloudflare page used for the answer.
- Use the Pages `llms.txt` index for discovery, then link the human docs URL in user-facing answers.
- Prefer `wrangler pages dev` for local development and `wrangler pages deploy <BUILD_OUTPUT_DIRECTORY>` for Direct Upload deployments.
- Keep static asset behavior in `_headers`, `_redirects`, `404.html`, and the build output directory when no Function needs to run.
- Keep Function behavior in Pages Functions code and control invocation with `_routes.json` when needed.
- Verify framework presets and limits at answer time because they change.
