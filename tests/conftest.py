"""
テストの共通設定
"""
import os
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_env():
    """テスト環境のセットアップ"""
    # テスト用の一時ディレクトリを作成
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)
    
    # テスト用の環境変数を設定
    os.environ["GEMINI_API_KEY_SUBSC"] = "dummy-key-for-test"
    
    yield
    
    # テスト後のクリーンアップ
    if test_dir.exists():
        for file in test_dir.glob("*"):
            if file.is_file():
                file.unlink()
        test_dir.rmdir() 