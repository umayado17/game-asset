# image2model.py
import asyncio, base64, json, os, anthropic
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import time
import logging
from anthropic._exceptions import OverloadedError

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = "claude-sonnet-4-20250514"        # Vision & tool-use 両対応

async def load_image_base64(path: str) -> str:
    logger.info(f"画像を読み込み中: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

async def retry_on_overload(func, max_retries=3, delay=2):
    last_error = None
    for i in range(max_retries):
        try:
            return await func()
        except OverloadedError as e:
            last_error = e
            if i == max_retries - 1:
                logger.error(f"最大リトライ回数({max_retries}回)に達しました。最後のエラー: {str(e)}")
                raise
            logger.warning(f"API overloaded, {delay}秒後にリトライします... (試行 {i+1}/{max_retries})")
            await asyncio.sleep(delay)
            delay *= 2  # 指数バックオフ
        except Exception as e:
            logger.error(f"予期せぬエラーが発生しました: {str(e)}")
            raise

async def main(img_path: str, user_prompt: str):
    r = None
    w = None
    try:
        logger.info("処理を開始します")
        logger.info(f"入力画像: {img_path}")
        logger.info(f"プロンプト: {user_prompt}")

        # 1. Blender MCP サーバーを起動 & 接続
        logger.info("Blender MCPサーバーを起動中...")
        server_cfg = StdioServerParameters(command="uvx", args=["blender-mcp"])
        async with stdio_client(server_cfg) as (r, w):
            async with ClientSession(r, w) as blender:
                logger.info("Blender MCPサーバーに接続しました")
                await blender.initialize()
                logger.info("Blender MCPサーバーの初期化が完了しました")

                # 2. Blenderのツール一覧をClaude用schemaへ変換
                logger.info("Blenderツール一覧を取得中...")
                raw_tools = await blender.list_tools()
                tools_schema = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.inputSchema,
                    }
                    for t in raw_tools.tools
                ]
                logger.info(f"利用可能なBlenderツール数: {len(tools_schema)}")

                # 3. Claudeへ初回リクエスト（画像＋プロンプト＋画像パス明示）
                logger.info("Claude APIに接続中...")
                async with anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY) as client:
                    img_b64 = await load_image_base64(img_path)
                    logger.info("画像の読み込みが完了しました")

                # 画像のbase64エンコーディングを確認
                logger.info(f"画像のbase64長さ: {len(img_b64)}")

                # リクエストの内容を確認（機密情報は除く）
                logger.info("送信するリクエストの内容:")
                logger.info(f"画像ブロックのtype: image")
                logger.info(f"画像ブロックのmedia_type: image/png")

                async def create_message():
                    logger.info("Claudeにメッセージを送信中...")
                    return await client.messages.create(
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
                                    "text": f"{user_prompt}。\n"
                                            f"元画像はローカルで `{img_path}` に保存されています。"
                                }
                            ]
                        }]
                    )

                try:
                    msg = await retry_on_overload(create_message)
                    logger.info("Claudeからの応答を受信しました")

                    # 4. Claude⇄Blender ループ
                    iteration = 1
                    max_iterations = 50  # 最大ループ回数を制限
                    messages = []  # メッセージ履歴を保持
                    final_text = []  # 最終的なテキスト応答を保持

                    while msg.stop_reason == "tool_use" and iteration <= max_iterations:
                        logger.info(f"ツール実行ループ {iteration}回目")
                        
                        # 応答の形式を確認
                        if not msg.content:
                            logger.error("応答が空です")
                            break
                            
                        # アシスタントのメッセージを保存
                        assistant_message_content = []
                        for block in msg.content:
                            if block.type == "text":
                                logger.info(f"Claudeの応答: {block.text}")
                                final_text.append(block.text)
                                assistant_message_content.append(block)
                            elif block.type == "tool_use":
                                logger.info(f"ツール呼び出し: {block.name}")
                                try:
                                    result = await blender.call_tool(block.name, block.input)
                                    logger.info(f"ツール実行完了: {block.name}")

                                    # ツールの実行結果を処理
                                    try:
                                        # MCPプロトコルに従って結果を処理
                                        if hasattr(result, 'content'):
                                            result_str = result.content
                                        elif hasattr(result, 'dict'):
                                            result_str = json.dumps(result.dict())
                                        elif hasattr(result, '__dict__'):
                                            result_str = json.dumps(result.__dict__)
                                        else:
                                            result_str = str(result)
                                    except Exception as e:
                                        logger.error(f"結果の変換中にエラーが発生しました: {str(e)}")
                                        result_str = str(result)

                                    # アシスタントのメッセージを追加
                                    messages.append({
                                        "role": "assistant",
                                        "content": assistant_message_content + [block]  # テキストブロックとツール使用ブロックを追加
                                    })

                                    # ツールの実行結果を追加
                                    messages.append({
                                        "role": "user",
                                        "content": [{
                                            "type": "tool_result",
                                            "tool_use_id": block.id,
                                            "content": result_str
                                        }]
                                    })

                                    # Claudeへ実行結果を返却
                                    logger.info("Claudeに実行結果を送信中...")

                                    async def _send_tool_results_to_claude():
                                        return await client.messages.create(
                                            model=MODEL,
                                            max_tokens=1024,
                                            tools=tools_schema,
                                            messages=messages
                                        )
                                    msg = await retry_on_overload(_send_tool_results_to_claude)
                                    
                                    logger.info("Claudeからの応答を受信しました")
                                except Exception as e:
                                    logger.error(f"ツール実行中にエラーが発生しました: {str(e)}")
                                    break
                        
                        iteration += 1

                    if iteration > max_iterations:
                        logger.warning(f"最大ループ回数({max_iterations}回)に達しました。処理を終了します。")

                    # 5. Claude の最終回答
                    logger.info("最終回答を出力します")
                    if msg.content:
                        for block in msg.content:
                            if block.type == "text":
                                final_text.append(block.text)
                                print(block.text)
                    else:
                        logger.error("応答が空です")
                    logger.info("処理が完了しました")
                except Exception as e:
                    logger.error(f"Claude APIとの通信中にエラーが発生しました: {str(e)}")
                    raise
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        raise
    finally:
        # finallyブロックは維持しますが、パイプの明示的なクローズ処理は削除します。
        # stdio_client のコンテキストマネージャがクローズを処理します。
        pass

if __name__ == "__main__":
    try:
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
            logger.info(f"選択されたファイル: {input_file}")
            asyncio.run(main(input_file, "これを Blender で 3D モデル化して"))
        else:
            logger.warning("ファイルが選択されませんでした")
            print("ファイルが選択されませんでした")
    except Exception as e:
        logger.error(f"プログラム実行中にエラーが発生しました: {str(e)}")
        raise
    finally:
        # 明示的にルートウィンドウを破棄
        if 'root' in locals():
            root.destroy()
