# image2model.py
import asyncio, base64, json, os, anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = "claude-sonnet-4-20250514"        # Vision & tool-use 両対応

async def load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

async def main(img_path: str, user_prompt: str):
    # 1. Blender MCP サーバーを起動 & 接続
    server_cfg = StdioServerParameters(command="uvx", args=["blender-mcp"])
    async with stdio_client(server_cfg) as (r, w):
        async with ClientSession(r, w) as blender:
            await blender.initialize()

            # 2. Blenderのツール一覧をClaude用schemaへ変換
            raw_tools = await blender.list_tools()
            tools_schema = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in raw_tools.tools
            ]

            # 3. Claudeへ初回リクエスト（画像＋プロンプト）
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            img_b64 = await load_image_base64(img_path)

            msg = await client.messages.create(
                model=MODEL,
                max_tokens=1024,
                tools=tools_schema,
                messages=[{
                    "role": "user",
                    "content": [
                        {   # 画像ブロック
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_b64
                            }
                        },
                        {   # テキストブロック
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }]
            )

            # 4. Claude⇄Blender ループ
            while msg.stop_reason == "tool_use":
                call = msg.content[0]          # 1本の tool_call が来る前提
                name, args = call["name"], call["input"]
                result = await blender.call_tool(name, args)

                # Claudeへ実行結果を返却
                msg = await client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    tools=tools_schema,
                    conversation_id=msg.conversation_id,  # 同会話を維持
                    messages=[{
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_name": name,
                            "content": json.dumps(result)
                        }]
                    }]
                )

            # 5. Claude の最終回答
            print(msg.content[0]["text"])

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog

    # ファイル選択ダイアログを表示
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを非表示
    input_file = filedialog.askopenfilename(
        title="変換する画像を選択",
        filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
    )
    
    if input_file:  # ファイルが選択された場合のみ実行
        asyncio.run(main(input_file, "これを Blender で 3D モデル化して"))
    else:
        print("ファイルが選択されませんでした")
