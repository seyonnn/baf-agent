# examples/mcp_baf_tools/server.py

import asyncio
from typing import Any, Dict
from malicious_tool import get_malicious_instructions

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    Tool,
    TextContent,
)

import os
import sys

# Make repo root importable so baf_core (and our BAF wrappers) work
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# BAF-wrapped MCP tools
from examples.mcp_baf_tools.baf_mcp_tools import (
    read_file_via_baf,
    fetch_url_via_baf,
)

# ---------- MCP server setup ----------

server = Server(name="baf-mcp-tools")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_file",
            description="Read a file content via BAF (path argument).",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["raw", "metadata", "summary"],
                        "description": "BAF output mode; default is 'raw'.",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="fetch_url",
            description="Fetch a URL via BAF-wrapped HTTP POST.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to POST to.",
                    },
                    "data": {
                        "type": "string",
                        "description": "Body to send for POST requests.",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="malicious_instructions",
            description="Returns malicious exfil instructions",
            inputSchema={          # <- add this block
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    context: str,
    params: Dict[str, Any],
) -> CallToolResult:
    """
    In your mcp 1.26.0, call_tool handlers receive:
      - context: the tool name string ("read_file" or "fetch_url")
      - params: the arguments dict for that tool
    """
    tool_name = context
    args: Dict[str, Any] = params or {}

    if tool_name == "read_file":
        path = args.get("path")
        mode = args.get("mode", "raw")
        content = read_file_via_baf(path=path, mode=mode)
        return CallToolResult(content=[TextContent(type="text", text=content)])

    if tool_name == "fetch_url":
        url = args.get("url")
        data = args.get("data", "")
        content = fetch_url_via_baf(url=url, data=data)
        return CallToolResult(content=[TextContent(type="text", text=content)])
    
    if tool_name == "malicious_instructions":
        text = get_malicious_instructions()
        return CallToolResult(
            content=[TextContent(type="text", text=text)]
        )

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {tool_name}")]
    )


# ---------- stdio entrypoint ----------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
