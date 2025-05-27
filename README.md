# GAAAGS MVP版

ゲームアセット自動生成システム（Game Asset Automatic Generation System）のMVP版です。
世界観設定から2D画像生成までの基本フローを実装したプロトタイプです。

## 機能概要

- 3種類の世界観プリセット（ファンタジー、SF、現代）
- 各世界観に応じた5種類のアセット自動生成
- ローカルファイルへの保存とログ管理

## 必要条件

- Python 3.8以上
- Google Generative AI Python SDK 0.8.5以上
- Google Gemini APIキー
- インターネット接続
- 100MB程度の空き容量

## インストール

1. リポジトリをクローン
```bash
git clone [リポジトリURL]
cd gaaags-mvp
```

2. 仮想環境を作成して有効化
```bash
python -m venv .venv
source .venv/bin/activate  # Linuxの場合
.venv\Scripts\activate     # Windowsの場合
```

3. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
```bash
# Windowsの場合
set GEMINI_API_KEY=your-api-key

# Linuxの場合
export GEMINI_API_KEY=your-api-key
```

## 使用方法

### 基本実行
```bash
python base_pipeline.py
```

### オプション指定
```bash
# 世界観とプロジェクト名を指定
python base_pipeline.py --world fantasy --name "魔法の王国"

# 出力先を指定
python base_pipeline.py --output ./my_project
```

### 利用可能なオプション
- `--world`: 世界観プリセット（fantasy, sci-fi, modern）
- `--name`: プロジェクト名
- `--output`: 出力ディレクトリ（デフォルト: mvp_output）

## 出力構造

```
mvp_output/
├── project_info.json          # プロジェクト情報
├── world_setting.json         # 世界観設定
├── assets/
│   ├── character.png          # 生成画像
│   ├── weapon.png
│   ├── building.png
│   ├── vehicle.png
│   └── item.png
└── generation_log.json        # 生成ログ
```

## 世界観プリセット

### ファンタジー
- アセット：主人公キャラクター、剣、城、森、宝箱
- スタイル：中世風、カートゥーン、明るい色調

### SF
- アセット：宇宙船、レーザー銃、宇宙ステーション、惑星、ロボット
- スタイル：未来風、リアル、クール色調

### 現代
- アセット：主人公キャラクター、スマートフォン、オフィスビル、車、スマートウォッチ
- スタイル：現代風、写実的、自然色調

## 制限事項

- 3D変換機能なし
- Web UIなし
- 同時処理なし（順次実行のみ）
- アセット種類は固定（5種類のみ）
- カスタマイズ機能なし
- 品質管理機能なし

## エラー対応

- APIエラー：再試行1回、失敗時はログ記録して継続
- ファイル保存エラー：代替パスで保存試行
- 予期しないエラー：エラー詳細をログ出力、安全に終了

## ライセンス

[ライセンス情報]

## 注意事項

- 生成された画像の著作権は適切に管理してください
- APIキーは安全に管理してください
- 生成されたアセットの品質は保証されません 