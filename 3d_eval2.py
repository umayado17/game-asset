# mcp_blender_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 1. MCPサーバーを subprocess で起動
    server = StdioServerParameters(
        command="uvx",           # pip install の場合は "python"
        args=["blender-mcp"],    # uvx blender-mcp と同じ
    )

    # 2. サーバープロセスと stdio で接続
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()          # 初期化ハンドシェイク
            tools = await session.list_tools()  # 使えるBlenderツール一覧
            print([t.name for t in tools.tools])

            # 例：立方体を作る
            await session.call_tool("create_cube", {"size": 2})

            # 例：シーン情報を取得
            info = await session.call_tool("get_scene_info", {})
            print(info)

asyncio.run(main())
