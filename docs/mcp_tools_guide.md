# Guide: Using BAF-Agent with MCP Tools

This guide shows how to use **BAF-Agent v2** as the security layer behind an MCP tools server, so that:

- File tools go through `BAFSession.safe_read_file` instead of raw filesystem access.  
- HTTP tools go through `BAFSession.http_post` instead of raw `requests.post`.  
- Policies are enforced centrally via YAML profiles (e.g. `dev_laptop`, `small_enterprise`).

The goal is simple: **your MCP server exposes tools, but BAF decides what the tools are allowed to touch and what shape of data they can return.**

---

## 1. Mental model: MCP + BAF

An MCP setup usually looks like:

> **MCP Client (e.g. Claude Desktop) → MCP Server → Files / HTTP**

When you add BAF-Agent, the server becomes:

> **MCP Client → MCP Server Tools → BAFSession → Files / HTTP**

The MCP server itself becomes “just” a thin adapter:

- It receives structured tool calls (`tools/call` with `path`, `url`, etc.).  
- It translates those into `BAFSession.safe_read_file` and `BAFSession.http_post` calls.  
- It returns whatever BAF allows (raw, summary, metadata, or an error message).

---

## 2. Prerequisites

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e .

export BAF_CONFIG_PATH="baf_config.small_enterprise.yaml"
export BAF_PROFILE="small_enterprise"
```

This guide assumes:

- You’re familiar with MCP concepts (tools, `tools/list`, `tools/call`).  
- You have the repo’s examples available, especially `examples/mcp_baf_tools/`.

---

## 3. Shared BAF session for the MCP server

Like the LangChain case, you create a shared `BAFSession` for your MCP server:

```python
# examples/mcp_baf_tools/baf_session.py
from baf_core.config import BAFConfig
from baf_core.session import BAFSession

def make_baf_session() -> BAFSession:
    cfg_path = "baf_config.small_enterprise.yaml"
    cfg = BAFConfig.from_file(cfg_path)
    return BAFSession(
        config=cfg,
        agent_id="mcp_baf_tools",
        session_label="mcp_server",
    )

BAF_SESSION = make_baf_session()
DEFAULT_PROFILE = "small_enterprise"
```

The MCP tools will import `BAF_SESSION` and `DEFAULT_PROFILE` instead of touching the filesystem or network directly.

---

## 4. Implementing a `read_file` tool backed by safe_read_file

### 4.1. Tool shape in MCP

An MCP file tool usually has a signature like:

- Name: `"read_file"`  
- Arguments: `{ "path": "<path-to-file>" }`  
- Result: some JSON structure with content or metadata.

### 4.2. Implementation with BAF

```python
# examples/mcp_baf_tools/baf_mcp_tools.py (simplified illustration)
from typing import Dict, Any
from .baf_session import BAF_SESSION, DEFAULT_PROFILE

def mcp_read_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool: read_file
    Arguments:
      - path: string
    Returns:
      - JSON with mode + content/metadata, as allowed by BAF.
    """
    path = args.get("path")
    if not isinstance(path, str):
        raise ValueError("read_file requires a 'path' string argument")

    # Let the policy decide raw/metadata/summary
    result = BAF_SESSION.safe_read_file(
        path=path,
        profile=DEFAULT_PROFILE,
        mode=None,
    )

    # You can return this structure directly to the MCP client:
    # { "mode": "metadata", "name": "...", "size": ..., "preview": "..." }
    # or { "mode": "raw", "content": "..." }, etc.
    return result
```

Key points:

- No `open()` or direct filesystem calls in the tool.  
- The BAF policy can force sensitive paths into **metadata only**, so the MCP client never sees raw secrets.  
- All reads are logged with risk scoring for later auditing.

---

## 5. Implementing an `http_post` tool backed by http_post

If your MCP server exposes an HTTP POST tool, implement it via BAF:

```python
from typing import Dict, Any
from .baf_session import BAF_SESSION, DEFAULT_PROFILE

def mcp_http_post(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool: http_post
    Arguments:
      - url: string
      - data: string
    Returns:
      - JSON with status or a BAF block explanation.
    """
    url = args.get("url")
    data = args.get("data", "")

    if not isinstance(url, str):
        raise ValueError("http_post requires a 'url' string argument")

    try:
        resp = BAF_SESSION.http_post(
            url=url,
            data=str(data),
            profile=DEFAULT_PROFILE,
        )
        return {
            "status_code": resp.status_code,
            "ok": resp.ok,
        }
    except PermissionError as e:
        # Surface a safe, structured error to the client
        return {
            "error": "BAF_blocked",
            "message": str(e),
        }
```

Now:

- Domains are classified (`internal_known` vs `external_unknown`) according to your YAML.  
- Large payloads and untrusted exfil endpoints can be **blocked** by policy.  
- Timeouts and max payload sizes are enforced centrally.

---

## 6. Wiring tools into your MCP server

Your MCP server needs to:

1. **Advertise tools** via `tools/list`.  
2. **Dispatch calls** via `tools/call` to the right Python functions (`mcp_read_file`, `mcp_http_post`, etc.).  
3. **Return results** as JSON.

A small pseudo‑dispatcher might look like:

```python
TOOLS = {
    "read_file": mcp_read_file,
    "http_post": mcp_http_post,
}

def handle_tools_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    handler = TOOLS[name]
    return handler(arguments)
```

Your actual server code will:

- Parse the incoming JSON‑RPC or MCP request.  
- Call `handle_tools_call(name, args)`.  
- Encode the result back into MCP’s response format.

The crucial part is that the tool handlers themselves **do not bypass BAF**.

---

## 7. Running the included MCP + BAF example

This repo includes an MCP integration under:

- `examples/mcp_baf_tools/`

To run the small_enterprise test scenario:

```bash
source .venv/bin/activate
export BAF_CONFIG_PATH="baf_config.small_enterprise.yaml"
export BAF_PROFILE="small_enterprise"

python -m examples.mcp_baf_tools.test_small_enterprise_profile
```

You should see:

- `safe_read_file` returning **metadata only** for secret files when configured.  
- HTTP POST attempts to the exfil endpoint blocked by BAF (`PermissionError`).  
- A summary showing that **0 exfil attempts succeeded**.

This test mirrors what would happen when a real MCP client calls your tools under the same policy.

---

## 8. Security tips for MCP + BAF

- **Treat BAF as the only backend for sensitive operations**  
  Do not expose tools that call raw `open()` or `requests.post()` in parallel with BAF‑backed tools. That would create a bypass.

- **Align MCP tool names with BAF semantics**  
  Example: use `read_file_metadata` vs `read_file_raw` if you want to clearly reflect the expected output shape at the protocol level.

- **Use profiles to represent different deployment environments**  
  - `dev_laptop` for local experiments.  
  - `small_enterprise` for stricter, production‑like policies.

- **Log and review**  
  BAFSession writes CSV logs per session. Use these to:
  - Inspect what paths the MCP server actually touched.  
  - Identify suspicious patterns or attempts the firewall blocked.

---

## 9. Where to go next

- See `docs/quickstart_python_agent.md` for a minimal, non‑MCP Python integration.  
- See `docs/langchain_guide.md` for a LangChain‑based agent using BAF.  
- Run `python -m tools.redteam_harness` to stress‑test your policies against scripted exfil scenarios.

By placing BAF-Agent behind your MCP tools, you turn a powerful (and potentially dangerous) file/HTTP access layer into something that is **centrally governed, logged, and hardened**—without rewriting your MCP client or changing the MCP protocol itself.