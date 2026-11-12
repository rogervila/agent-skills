---
name: "Equipment MCP Server"
description: "Build, configure, test, and deploy the FastMCP server included in Equipment 1.4.0 project templates."
tags: [equipment, mcp, fastmcp, model-context-protocol, mcpserver.py, tools, resources, prompts, stdio, streamable-http, testing, security]
---

# Equipment MCP Server

Equipment 1.4.0 adds an optional FastMCP server to generated projects. This is template code, not an API provided by the installed `equipment` package. Read the generated `mcpserver.py`, `config/mcp.yaml`, and `pyproject.toml` before changing a project; templates may differ because `equipment new` downloads the current `main` branch.

Official guide: https://equipment-python.vercel.app/docs/examples/mcp

## Files And Dependency

The generated project includes:

- `mcpserver.py`: FastMCP server exposing the sample service as a tool, resource, and prompt.
- `config/mcp.yaml`: transport and HTTP endpoint configuration.
- `tests/test_mcpserver.py`: tests using FastMCP's in-memory client.
- `fastmcp>=4.1.7,<5` in `pyproject.toml`.

FastMCP may ship breaking changes in minor versions. Pin the exact version tested for production. If the project does not use MCP, remove the entry point, config, tests, and `fastmcp` dependency together.

Do not name a project module or directory `mcp`; it shadows the MCP SDK imported by FastMCP and can produce `ImportError: FastMCP server support is not installed`.

## Configuration And Transports

`config/mcp.yaml`:

```yaml
mcp:
  transport: ${MCP_TRANSPORT:stdio}
  host: ${MCP_HOST:127.0.0.1}
  port: ${MCP_PORT:8001}
  path: ${MCP_PATH:/mcp}
```

| Variable | Default | Use |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` for a local client-launched process; `http` for Streamable HTTP. |
| `MCP_HOST` | `127.0.0.1` | HTTP bind host. |
| `MCP_PORT` | `8001` | HTTP port; separate from the FastAPI default `8000`. |
| `MCP_PATH` | `/mcp` | HTTP endpoint path. |

With `stdio`, the MCP client starts `mcpserver.py`; do not launch a separate server process. With HTTP, run `python mcpserver.py` from the project root and connect to `http://HOST:PORT/PATH`. Start either process with the interpreter where the project and FastMCP are installed.

FastMCP reads additional `FASTMCP_*` settings from the environment. Equipment config is loaded from the working directory, so configure the MCP client's working directory as the project root.

## Tools, Resources, And Prompts

Register MCP handlers in `mcpserver.py` or split them into modules under `app/` and register them from the entry point.

- Tools invoke actions or return results. Type hints define the input schema; docstrings describe the operation to clients.
- Resources expose read-only content by URI.
- Prompts provide reusable message templates.

Keep handlers small and delegate business logic to services registered on `App`. Use sync `def` handlers for blocking Equipment calls such as database, storage, queue, and `requests` operations. Use `async def` only when all calls in the handler are non-blocking.

FastMCP supports provider injection with `fastmcp.dependencies.Depends`; injected parameters do not appear in the tool schema. Direct calls such as `app.inspiring()` are also used by the generated template. When editing its entry point, prefer `application = app()` over rebinding the imported factory, so the file can be type-checked.

The generated server sets `mask_error_details=True`. Ordinary exceptions return generic errors to clients while details go to stderr and MCP logs. Raise `fastmcp.exceptions.ToolError` only when the model should see the message; never include secrets, paths, credentials, or other sensitive details.

## Testing

Use the FastMCP in-memory `Client` with the server object. Tests need no subprocess or network:

```bash
python -m unittest tests.test_mcpserver
```

Test that tools, resources, and prompts are registered, then exercise their observable results. For service behavior, test the service directly; reserve MCP tests for protocol-facing behavior.

The server and tests share the cached `App` container. Override providers before calling the server and register cleanup for every override, for example `self.addCleanup(self.app.inspiring.reset_override)`. The generated test class skips when `fastmcp` is not installed; keep the dependency installed when expecting those tests to run.

## Serve MCP With FastAPI

To share the HTTP port with FastAPI, mount FastMCP's HTTP app in `web.py` and use the MCP app lifespan so its session manager starts. If FastAPI already defines a lifespan, combine both lifespans with FastMCP's `combine_lifespans`. Follow the current [official example](https://equipment-python.vercel.app/docs/examples/mcp) for exact code; do not mount only the route without the lifespan.

## Security And Operations

- Never print to stdout with `stdio`; stdout carries MCP protocol messages. Use `app.log()` or stderr.
- HTTP MCP has no authentication by default. Keep remote access on a private network or behind a gateway, or configure FastMCP authentication.
- The generated `host_origin_protection='auto'` protects loopback requests against Host/Origin abuse. It does not validate requests arriving through other network interfaces.
- For a public hostname, configure explicit allowed hosts and authentication. Do not rely on loopback protection when binding `MCP_HOST=0.0.0.0`.
- MCP tools can invoke application capabilities. Validate arguments and paths, authorize sensitive actions, and do not pass untrusted input directly to storage paths or SQL.
- For multiple HTTP workers, set `FASTMCP_STATELESS_HTTP=true` when requests cannot depend on in-memory sessions.
- `equipment compile` compiles `mcpserver.py`, but does not bundle FastMCP or other third-party dependencies. Install project dependencies on the target.

## Best Practices

- Keep tool schemas and docstrings clear; clients use them to select and call tools.
- Use typed, thin handlers and Equipment services for business behavior.
- Run MCP tests with the in-memory client and restore every shared-container override.
- Reserve stdout for protocol messages with `stdio`.
- Protect HTTP MCP with authentication and network controls.
- Start the server from the project root with the project's Python interpreter.
