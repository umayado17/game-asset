"""
PromptBuilderクラスのテスト
"""
import pytest
from base_pipeline import PromptBuilder, WorldSetting, AssetSpec

@pytest.fixture
def prompt_builder():
    """PromptBuilderのフィクスチャ"""
    return PromptBuilder()

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
def asset_spec():
    """AssetSpecのフィクスチャ"""
    return AssetSpec(
        name="テストアセット",
        category="character",
        description="テスト用アセット",
        tags=["test", "character"]
    )

def test_build_prompt_fantasy(prompt_builder, world_setting, asset_spec):
    """ファンタジー世界観のプロンプト生成テスト"""
    world_setting.genre = "fantasy"
    prompt = prompt_builder.build_prompt(world_setting, asset_spec)
    
    assert "medieval fantasy" in prompt
    assert "bright and magical" in prompt
    assert "enchanted" in prompt
    assert asset_spec.name in prompt
    assert "game asset" in prompt

def test_build_prompt_scifi(prompt_builder, world_setting, asset_spec):
    """SF世界観のプロンプト生成テスト"""
    world_setting.genre = "sci-fi"
    prompt = prompt_builder.build_prompt(world_setting, asset_spec)
    
    assert "futuristic" in prompt
    assert "cool and high-tech" in prompt
    assert "sci-fi" in prompt
    assert asset_spec.name in prompt
    assert "game asset" in prompt

def test_build_prompt_modern(prompt_builder, world_setting, asset_spec):
    """現代世界観のプロンプト生成テスト"""
    world_setting.genre = "modern"
    prompt = prompt_builder.build_prompt(world_setting, asset_spec)
    
    assert "realistic" in prompt
    assert "natural" in prompt
    assert "contemporary" in prompt
    assert asset_spec.name in prompt
    assert "game asset" in prompt 