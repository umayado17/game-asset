"""
AssetPipelineクラスのテスト
"""
import os
import pytest
from pathlib import Path
from base_pipeline import AssetPipeline, WorldSetting, APIKeyError, ConfigurationError
from datetime import datetime

@pytest.fixture
def api_key():
    """テスト用APIキーのフィクスチャ"""
    return os.getenv("GEMINI_API_KEY_SUBSC") or os.getenv("GEMINI_API_KEY") or "dummy-key-for-test"

@pytest.fixture
def world_setting():
    """WorldSettingのフィクスチャ"""
    return WorldSetting(
        name="テスト世界",
        genre="fantasy",
        art_style="cartoon",
        color_palette="bright",
        theme="adventure",
        description="テスト用の世界観設定"
    )

@pytest.fixture
def asset_pipeline(api_key, world_setting):
    """AssetPipelineのフィクスチャ"""
    pipeline = AssetPipeline(api_key)
    pipeline.world_setting = world_setting
    return pipeline

def test_init_without_api_key():
    """APIキーなしでの初期化テスト"""
    with pytest.raises(APIKeyError):
        AssetPipeline(None)

def test_get_asset_specs_fantasy(asset_pipeline, world_setting):
    """ファンタジー世界観のアセット仕様取得テスト"""
    world_setting.genre = "fantasy"
    specs = asset_pipeline.get_asset_specs(world_setting)
    assert len(specs) == 5
    assert specs[0].name == "主人公キャラクター"
    assert specs[1].name == "剣"
    assert specs[2].name == "城"
    assert specs[3].name == "森"
    assert specs[4].name == "宝箱"

def test_get_asset_specs_scifi(asset_pipeline, world_setting):
    """SF世界観のアセット仕様取得テスト"""
    world_setting.genre = "sci-fi"
    specs = asset_pipeline.get_asset_specs(world_setting)
    assert len(specs) == 5
    assert specs[0].name == "宇宙船"
    assert specs[1].name == "レーザー銃"
    assert specs[2].name == "宇宙ステーション"
    assert specs[3].name == "惑星"
    assert specs[4].name == "ロボット"

def test_get_asset_specs_modern(asset_pipeline, world_setting):
    """現代世界観のアセット仕様取得テスト"""
    world_setting.genre = "modern"
    specs = asset_pipeline.get_asset_specs(world_setting)
    assert len(specs) == 5
    assert specs[0].name == "主人公キャラクター"
    assert specs[1].name == "スマートフォン"
    assert specs[2].name == "オフィスビル"
    assert specs[3].name == "車"
    assert specs[4].name == "スマートウォッチ"

def test_process_world(asset_pipeline, world_setting):
    """世界観処理テスト"""
    assets = asset_pipeline.process_world(world_setting)
    assert len(assets) == 5
    for asset in assets:
        assert asset.status in ["generated", "failed"]

    # 出力ディレクトリの検証
    project_dirs = list(asset_pipeline.file_manager.output_dir.glob(f"{world_setting.name}_*"))
    assert len(project_dirs) == 1
    
    project_dir = project_dirs[0]
    assert (project_dir / "project_info.json").exists()
    assert (project_dir / "world_setting.json").exists()
    assert (project_dir / "generation_log.json").exists()
    assert (project_dir / "assets").exists() 