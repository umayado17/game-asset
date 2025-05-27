"""
FileManagerクラスのテスト
"""
import os
import json
import pytest
from pathlib import Path
from datetime import datetime
from base_pipeline import FileManager, WorldSetting, GeneratedAsset, AssetSpec

@pytest.fixture
def temp_dir(tmp_path):
    """一時ディレクトリのフィクスチャ"""
    return tmp_path

@pytest.fixture
def file_manager(temp_dir):
    """FileManagerのフィクスチャ"""
    return FileManager(str(temp_dir))

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
def generated_asset(world_setting):
    """GeneratedAssetのフィクスチャ"""
    spec = AssetSpec(
        name="テストアセット",
        category="character",
        description="テスト用アセット",
        tags=["test", "character"]
    )
    return GeneratedAsset(
        id="test_asset_1",
        spec=spec,
        world_setting=world_setting,
        image_path="test.png",
        prompt_used="test prompt",
        created_at=datetime.now(),
        status="generated"
    )

def test_init(file_manager, temp_dir):
    """初期化テスト"""
    assert file_manager.output_dir == temp_dir
    assert temp_dir.exists()

def test_save_project_info(file_manager, world_setting, temp_dir):
    """プロジェクト情報保存テスト"""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    
    file_manager.save_project_info(world_setting, project_dir)
    
    info_file = project_dir / "project_info.json"
    assert info_file.exists()
    
    with open(info_file, "r", encoding="utf-8") as f:
        info = json.load(f)
        assert info["name"] == world_setting.name
        assert info["world_preset"] == world_setting.genre

def test_save_world_setting(file_manager, world_setting, temp_dir):
    """世界観設定保存テスト"""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    
    file_manager.save_world_setting(world_setting, project_dir)
    
    setting_file = project_dir / "world_setting.json"
    assert setting_file.exists()
    
    with open(setting_file, "r", encoding="utf-8") as f:
        setting = json.load(f)
        assert setting["name"] == world_setting.name
        assert setting["genre"] == world_setting.genre

def test_save_generation_log(file_manager, generated_asset, temp_dir):
    """生成ログ保存テスト"""
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()
    
    file_manager.save_generation_log([generated_asset], project_dir)
    
    log_file = project_dir / "generation_log.json"
    assert log_file.exists()
    
    with open(log_file, "r", encoding="utf-8") as f:
        log = json.load(f)
        assert len(log) == 1
        assert log[0]["asset_name"] == generated_asset.spec.name
        assert log[0]["status"] == generated_asset.status 