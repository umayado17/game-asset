"""
GAAAGS MVP版 パイプライン
世界観設定から2D画像生成までの基本フローを実装
"""

import json
import os
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64

class GAAAGSError(Exception):
    """GAAAGSの基本例外クラス"""
    pass

class APIKeyError(GAAAGSError):
    """APIキー関連のエラー"""
    pass

class FileOperationError(GAAAGSError):
    """ファイル操作関連のエラー"""
    pass

class ImageGenerationError(GAAAGSError):
    """画像生成関連のエラー"""
    pass

class ConfigurationError(GAAAGSError):
    """設定関連のエラー"""
    pass

@dataclass
class WorldSetting:
    """世界観設定"""
    name: str
    genre: str  # fantasy, sci-fi, modern
    art_style: str  # realistic, cartoon, pixel
    color_palette: str  # dark, bright, vibrant
    theme: str  # adventure, horror, peaceful
    description: str

@dataclass
class AssetSpec:
    """アセット仕様"""
    name: str
    category: str  # character, weapon, building, vehicle, item
    description: str
    tags: List[str]

@dataclass
class GeneratedAsset:
    """生成済みアセット"""
    id: str
    spec: AssetSpec
    world_setting: WorldSetting
    image_path: str
    prompt_used: str
    created_at: datetime
    status: str  # generated, failed

class FileManager:
    """ファイル管理"""
    
    def __init__(self, output_dir: str = "mvp_output"):
        try:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(exist_ok=True)
        except Exception as e:
            raise FileOperationError(f"出力ディレクトリの作成に失敗: {e}")
    
    def save_project_info(self, world_setting: WorldSetting, project_dir: Path):
        """プロジェクト情報を保存"""
        try:
            info = {
                "name": world_setting.name,
                "created_at": datetime.now().isoformat(),
                "world_preset": world_setting.genre
            }
            
            with open(project_dir / "project_info.json", "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise FileOperationError(f"プロジェクト情報の保存に失敗: {e}")
    
    def save_world_setting(self, world_setting: WorldSetting, project_dir: Path):
        """世界観設定を保存"""
        try:
            with open(project_dir / "world_setting.json", "w", encoding="utf-8") as f:
                json.dump(asdict(world_setting), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise FileOperationError(f"世界観設定の保存に失敗: {e}")
    
    def save_generation_log(self, assets: List[GeneratedAsset], project_dir: Path):
        """生成ログを保存"""
        try:
            log = []
            for asset in assets:
                log.append({
                    "asset_name": asset.spec.name,
                    "prompt": asset.prompt_used,
                    "status": asset.status,
                    "file_path": str(asset.image_path),
                    "generated_at": asset.created_at.isoformat()
                })
            
            with open(project_dir / "generation_log.json", "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise FileOperationError(f"生成ログの保存に失敗: {e}")

class PromptBuilder:
    """プロンプト生成"""
    
    def __init__(self):
        self.templates = {
            "fantasy": {
                "art_style": "medieval fantasy",
                "color_palette": "bright and magical",
                "theme": "enchanted"
            },
            "sci-fi": {
                "art_style": "futuristic",
                "color_palette": "cool and high-tech",
                "theme": "sci-fi"
            },
            "modern": {
                "art_style": "realistic",
                "color_palette": "natural",
                "theme": "contemporary"
            }
        }
    
    def build_prompt(self, world_setting: WorldSetting, asset_spec: AssetSpec) -> str:
        """テンプレートベースでプロンプトを生成"""
        template = self.templates[world_setting.genre]
        
        prompt = f"{template['art_style']} style {asset_spec.name} for a {world_setting.genre} game, "
        prompt += f"{template['color_palette']} color palette, {template['theme']} atmosphere, "
        prompt += "high quality, game asset, white background"
        
        return prompt

class GeminiImageGenerator:
    """Geminiを使った画像生成"""
    
    def __init__(self, api_key: str):
        if not api_key or api_key == "your-gemini-api-key":
            raise APIKeyError("APIキーが設定されていません")
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-preview-image-generation')
        except Exception as e:
            raise ConfigurationError(f"Gemini APIの初期化に失敗: {e}")
    
    def generate_image(self, prompt: str, output_path: Path) -> bool:
        """画像を生成して保存"""
        try:
            # 画像生成リクエスト
            response = self.model.generate_content(
                contents=prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            
            # 生成された画像を保存
            if response.image:
                try:
                    with open(output_path, 'wb') as f:
                        f.write(response.image)
                    return True
                except Exception as e:
                    raise FileOperationError(f"画像の保存に失敗: {e}")
            else:
                raise ImageGenerationError(f"画像生成に失敗: {response.text}")
            
        except ImageGenerationError:
            raise
        except Exception as e:
            raise ImageGenerationError(f"画像生成中にエラーが発生: {e}")

class AssetPipeline:
    """メインパイプライン"""
    
    def __init__(self, api_key: str):
        try:
            self.file_manager = FileManager()
            self.prompt_builder = PromptBuilder()
            self.image_generator = GeminiImageGenerator(api_key)
            # デフォルトの世界観設定を初期化
            self.world_setting = WorldSetting(
                name="テスト世界",
                genre="fantasy",
                art_style="cartoon",
                color_palette="bright",
                theme="adventure",
                description="テスト用の世界観設定"
            )
        except Exception as e:
            raise ConfigurationError(f"パイプラインの初期化に失敗: {e}")
    
    def get_asset_specs(self, world_setting: WorldSetting) -> List[AssetSpec]:
        """世界観に基づいてアセット仕様を取得"""
        specs = {
            "fantasy": [
                AssetSpec("主人公キャラクター", "character", "プレイヤーが操作するメインキャラクター", ["hero", "protagonist"]),
                AssetSpec("剣", "weapon", "主人公の武器", ["sword", "weapon"]),
                AssetSpec("城", "building", "メインの拠点", ["castle", "building"]),
                AssetSpec("森", "environment", "冒険の舞台", ["forest", "nature"]),
                AssetSpec("宝箱", "item", "アイテムを収納", ["treasure", "chest"])
            ],
            "sci-fi": [
                AssetSpec("宇宙船", "vehicle", "プレイヤーの乗り物", ["spaceship", "vehicle"]),
                AssetSpec("レーザー銃", "weapon", "未来の武器", ["laser", "weapon"]),
                AssetSpec("宇宙ステーション", "building", "メインの拠点", ["station", "building"]),
                AssetSpec("惑星", "environment", "探索の舞台", ["planet", "space"]),
                AssetSpec("ロボット", "character", "AI仲間", ["robot", "ai"])
            ],
            "modern": [
                AssetSpec("主人公キャラクター", "character", "プレイヤーが操作するメインキャラクター", ["hero", "protagonist"]),
                AssetSpec("スマートフォン", "item", "現代の必須アイテム", ["phone", "device"]),
                AssetSpec("オフィスビル", "building", "メインの拠点", ["office", "building"]),
                AssetSpec("車", "vehicle", "移動手段", ["car", "vehicle"]),
                AssetSpec("スマートウォッチ", "item", "装備品", ["watch", "device"])
            ]
        }
        
        return specs.get(world_setting.genre, specs["fantasy"])
    
    def process_world(self, world_setting: WorldSetting) -> List[GeneratedAsset]:
        """世界観を処理してアセットを生成"""
        try:
            print(f"世界観 '{world_setting.name}' の処理を開始...")
            
            # プロジェクトディレクトリ作成
            project_dir = self.file_manager.output_dir / f"{world_setting.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_dir.mkdir(exist_ok=True)
            (project_dir / "assets").mkdir(exist_ok=True)
            
            # プロジェクト情報保存
            self.file_manager.save_project_info(world_setting, project_dir)
            self.file_manager.save_world_setting(world_setting, project_dir)
            
            # アセット生成
            asset_specs = self.get_asset_specs(world_setting)
            print(f"{len(asset_specs)}個のアセットを生成予定")
            
            generated_assets = []
            
            for i, spec in enumerate(asset_specs, 1):
                try:
                    print(f"[{i}/5] {spec.name}生成中...")
                    
                    # プロンプト生成
                    prompt = self.prompt_builder.build_prompt(world_setting, spec)
                    
                    # 画像生成
                    image_path = project_dir / "assets" / f"{spec.name}.png"
                    success = self.image_generator.generate_image(prompt, image_path)
                    
                    # アセット作成
                    asset = GeneratedAsset(
                        id=f"{world_setting.name}_{spec.name}",
                        spec=spec,
                        world_setting=world_setting,
                        image_path=str(image_path),
                        prompt_used=prompt,
                        created_at=datetime.now(),
                        status="generated" if success else "failed"
                    )
                    
                    generated_assets.append(asset)
                    print(f"✓ {spec.name} 生成{'完了' if success else '失敗'}")
                except Exception as e:
                    print(f"✗ {spec.name} 生成中にエラー: {e}")
                    # エラーが発生しても処理を継続
                    continue
            
            # 生成ログ保存
            self.file_manager.save_generation_log(generated_assets, project_dir)
            
            print(f"世界観 '{world_setting.name}' の処理完了: {len(generated_assets)}個生成")
            print(f"出力フォルダ: {project_dir}")
            return generated_assets
            
        except Exception as e:
            raise GAAAGSError(f"世界観処理中にエラーが発生: {e}")

def main():
    """メイン実行"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description="GAAAGS MVP版")
        parser.add_argument("--world", choices=["fantasy", "sci-fi", "modern"], default="fantasy",
                          help="世界観プリセット")
        parser.add_argument("--name", default="新しい世界",
                          help="プロジェクト名")
        parser.add_argument("--output", default="mvp_output",
                          help="出力ディレクトリ")
        args = parser.parse_args()
        
        # API key設定（環境変数から取得）
        API_KEY = os.getenv("GEMINI_API_KEY_SUBSC") or os.getenv("GEMINI_API_KEY")
        if not API_KEY:
            raise APIKeyError("環境変数 'GEMINI_API_KEY_SUBSC' または 'GEMINI_API_KEY' が設定されていません")
        
        # パイプライン初期化
        pipeline = AssetPipeline(API_KEY)
        
        # 世界観設定
        world_setting = WorldSetting(
            name=args.name,
            genre=args.world,
            art_style="cartoon" if args.world == "fantasy" else "realistic",
            color_palette="bright" if args.world == "fantasy" else "cool",
            theme="adventure" if args.world == "fantasy" else "sci-fi",
            description=f"{args.world}の世界観で{args.name}を表現"
        )
        
        # アセット生成実行
        assets = pipeline.process_world(world_setting)
        
        # 結果表示
        print(f"\n=== 生成結果 ===")
        for asset in assets:
            print(f"- {asset.spec.name}: {asset.status}")
            
    except APIKeyError as e:
        print(f"エラー: APIキーの設定が必要です: {e}")
        sys.exit(1)
    except FileOperationError as e:
        print(f"エラー: ファイル操作に失敗しました: {e}")
        sys.exit(1)
    except ImageGenerationError as e:
        print(f"エラー: 画像生成に失敗しました: {e}")
        sys.exit(1)
    except ConfigurationError as e:
        print(f"エラー: 設定に問題があります: {e}")
        sys.exit(1)
    except GAAAGSError as e:
        print(f"エラー: 予期せぬエラーが発生しました: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 予期せぬエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()