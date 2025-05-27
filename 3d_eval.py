import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import time
from datetime import datetime

@dataclass
class ConversionSettings:
    """3D変換設定"""
    quality: str = "medium"  # low, medium, high
    poly_count_limit: int = 5000
    texture_size: int = 1024
    generate_lod: bool = True
    export_format: str = "fbx"  # fbx, obj, gltf
    
    @property
    def displacement_strength(self) -> float:
        """品質に応じたディスプレースメント強度を返す"""
        return {
            "low": 0.05,
            "medium": 0.1,
            "high": 0.2
        }.get(self.quality, 0.1)
    
    @property
    def poly_limit(self) -> int:
        """品質に応じたポリゴン数制限を返す"""
        return {
            "low": 1000,
            "medium": 5000,
            "high": 10000
        }.get(self.quality, 5000)

@dataclass
class ConversionMetadata:
    """変換メタデータ"""
    model_info: Dict
    conversion_info: Dict
    
    def save(self, output_path: str):
        """メタデータをJSONファイルとして保存"""
        metadata_path = Path(output_path).parent / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                "model_info": self.model_info,
                "conversion_info": self.conversion_info
            }, f, indent=2, ensure_ascii=False)

class BlenderMCPConverter:
    """Blender-MCPを使った3D変換"""
    
    def __init__(self, blender_path: str = None):
        self.blender_path = blender_path or self.find_blender()
        self.mcp_script_path = Path("blender_mcp_script.py")
        self.setup_mcp_script()
        self.max_retries = 3
        self.error_log = []
    
    def find_blender(self) -> str:
        """Blenderの実行ファイルを探す"""
        common_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            "blender"  # PATH通っている場合
        ]
        
        for path in common_paths:
            if os.path.exists(path) or path == "blender":
                try:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"Blender found: {path}")
                        return path
                except:
                    continue
        
        raise FileNotFoundError("Blenderが見つかりません。パスを指定してください。")
    
    def setup_mcp_script(self):
        """Blender内で実行するMCPスクリプトを準備"""
        
        script_content = '''
import bpy
import bmesh
import os
import sys
from mathutils import Vector

def clear_scene():
    """シーンをクリア"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_plane_with_image(image_path, settings):
    """2D画像から3Dプレーンを作成"""
    
    # 画像読み込み
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return None
    
    # プレーン作成
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.active_object
    
    # マテリアル作成
    material = bpy.data.materials.new(name="ImageMaterial")
    material.use_nodes = True
    plane.data.materials.append(material)
    
    # ノード設定
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    # 既存ノードクリア
    nodes.clear()
    
    # プリンシプルBSDFノード
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    
    # 画像テクスチャノード
    image = bpy.data.images.load(image_path)
    
    # テクスチャサイズの調整
    if image.size[0] > settings.get('texture_size', 1024) or image.size[1] > settings.get('texture_size', 1024):
        image.scale(settings.get('texture_size', 1024), settings.get('texture_size', 1024))
    
    image_node = nodes.new('ShaderNodeTexImage')
    image_node.image = image
    
    # 出力ノード
    output = nodes.new('ShaderNodeOutputMaterial')
    
    # ノード接続
    links.new(image_node.outputs['Color'], principled.inputs['Base Color'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])
    
    return plane

def generate_lod(obj, quality_levels):
    """LODを生成"""
    lods = []
    original_poly_count = len(obj.data.polygons)
    
    for level, ratio in quality_levels.items():
        if level == "high":
            lods.append(obj)
            continue
            
        # デシメート修飾子でポリゴン数削減
        decimate = obj.modifiers.new(name=f"Decimate_{level}", type='DECIMATE')
        decimate.type = 'RATIO'
        decimate.ratio = ratio
        
        # 修飾子適用
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        lods.append(obj)
    
    return lods

def apply_displacement_from_image(obj, image_path, strength=0.1):
    """画像の明度に基づいてディスプレースメントを適用"""
    
    # サブディビジョンサーフェス追加
    subdiv = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 2
    
    # ディスプレースメント修飾子追加
    displace = obj.modifiers.new(name="Displace", type='DISPLACE')
    
    # ディスプレースメント用テクスチャ作成
    texture = bpy.data.textures.new(name="DisplaceTexture", type='IMAGE')
    texture.image = bpy.data.images.load(image_path)
    
    displace.texture = texture
    displace.strength = strength
    displace.mid_level = 0.5

def optimize_mesh(obj, poly_limit):
    """メッシュを最適化"""
    
    # デシメート修飾子でポリゴン数削減
    decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
    decimate.type = 'RATIO'
    
    # 現在のポリゴン数取得
    current_polys = len(obj.data.polygons)
    if current_polys > poly_limit:
        decimate.ratio = poly_limit / current_polys
    
    # 修飾子適用
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=decimate.name)

def export_model(obj, output_path, format_type, generate_lod=False):
    """モデルをエクスポート"""
    
    if generate_lod:
        # LOD生成
        quality_levels = {
            "high": 1.0,
            "medium": 0.5,
            "low": 0.25
        }
        lods = generate_lod(obj, quality_levels)
        
        # 各LODをエクスポート
        for level, lod_obj in zip(quality_levels.keys(), lods):
            output_dir = os.path.dirname(output_path)
            lod_path = os.path.join(output_dir, level, os.path.basename(output_path))
            os.makedirs(os.path.dirname(lod_path), exist_ok=True)
            
            # オブジェクト選択
            bpy.ops.object.select_all(action='DESELECT')
            lod_obj.select_set(True)
            bpy.context.view_layer.objects.active = lod_obj
            
            # フォーマットに応じてエクスポート
            if format_type.lower() == 'fbx':
                bpy.ops.export_scene.fbx(
                    filepath=lod_path,
                    use_selection=True,
                    embed_textures=True
                )
            elif format_type.lower() == 'obj':
                bpy.ops.export_scene.obj(
                    filepath=lod_path,
                    use_selection=True
                )
            elif format_type.lower() == 'gltf':
                bpy.ops.export_scene.gltf(
                    filepath=lod_path,
                    use_selection=True,
                    export_format='GLB'
                )
    else:
        # 通常のエクスポート
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        if format_type.lower() == 'fbx':
            bpy.ops.export_scene.fbx(
                filepath=output_path,
                use_selection=True,
                embed_textures=True
            )
        elif format_type.lower() == 'obj':
            bpy.ops.export_scene.obj(
                filepath=output_path,
                use_selection=True
            )
        elif format_type.lower() == 'gltf':
            bpy.ops.export_scene.gltf(
                filepath=output_path,
                use_selection=True,
                export_format='GLB'
            )

def main():
    """メイン処理"""
    
    # コマンドライン引数取得
    if len(sys.argv) < 6:
        print("Usage: blender --background --python script.py -- <image_path> <output_path> <settings_json>")
        return
    
    # '--'以降の引数を取得
    try:
        separator_index = sys.argv.index('--')
        args = sys.argv[separator_index + 1:]
    except ValueError:
        print("Arguments should be passed after '--'")
        return
    
    image_path = args[0]
    output_path = args[1]
    settings_json = args[2]
    
    # 設定読み込み
    import json
    settings = json.loads(settings_json)
    
    print(f"Converting {image_path} to {output_path}")
    print(f"Settings: {settings}")
    
    # シーンクリア
    clear_scene()
    
    # 2D画像から3Dモデル作成
    obj = create_plane_with_image(image_path, settings)
    if not obj:
        print("Failed to create model")
        return
    
    # 品質に応じて処理を変更
    if settings.get('quality') in ['medium', 'high']:
        # ディスプレースメント適用
        apply_displacement_from_image(obj, image_path, 
                                    strength=settings.get('displacement_strength', 0.1))
    
    # メッシュ最適化
    optimize_mesh(obj, settings.get('poly_count_limit', 5000))
    
    # エクスポート
    export_model(obj, output_path, settings.get('export_format', 'fbx'),
                generate_lod=settings.get('generate_lod', False))
    
    print(f"Conversion completed: {output_path}")

if __name__ == "__main__":
    main()
'''
        
        with open(self.mcp_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
    
    def log_error(self, error_type: str, message: str, details: Dict = None):
        """エラーをログに記録"""
        self.error_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
            "details": details or {}
        })
    
    def batch_convert(self, image_paths: list, output_dir: str, 
                     settings: ConversionSettings = None) -> Dict[str, str]:
        """複数の画像をバッチ処理で変換"""
        if len(image_paths) > 10:
            raise ValueError("最大10ファイルまで同時処理可能です")
        
        results = {}
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 品質別の出力ディレクトリを作成
        quality_dirs = {
            "low": output_dir / "low",
            "medium": output_dir / "medium",
            "high": output_dir / "high"
        }
        for dir_path in quality_dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        for image_path in image_paths:
            image_path = Path(image_path)
            quality = settings.quality if settings else "medium"
            output_path = quality_dirs[quality] / f"{image_path.stem}.{settings.export_format}"
            
            # 最大3回までリトライ
            for attempt in range(self.max_retries):
                try:
                    result = self.convert_to_3d(str(image_path), str(output_path), settings)
                    if result:
                        results[str(image_path)] = result
                        break
                    else:
                        self.log_error("conversion_failed", 
                                     f"変換失敗 (試行 {attempt + 1}/{self.max_retries})",
                                     {"image_path": str(image_path)})
                except Exception as e:
                    self.log_error("conversion_error",
                                 str(e),
                                 {"image_path": str(image_path), "attempt": attempt + 1})
                    if attempt == self.max_retries - 1:
                        results[str(image_path)] = None
        
        # エラーログを保存
        if self.error_log:
            log_path = output_dir / "error_log.json"
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.error_log, f, indent=2, ensure_ascii=False)
        
        return results
    
    def convert_to_3d(self, image_path: str, output_path: str, 
                     settings: ConversionSettings = None) -> Optional[str]:
        """2D画像を3Dモデルに変換"""
        
        if settings is None:
            settings = ConversionSettings()
        
        start_time = time.time()
        
        # 設定をJSONで渡す
        settings_json = json.dumps({
            'quality': settings.quality,
            'poly_count_limit': settings.poly_limit,
            'texture_size': settings.texture_size,
            'generate_lod': settings.generate_lod,
            'export_format': settings.export_format
        })
        
        # Blenderコマンド構築
        cmd = [
            self.blender_path,
            '--background',
            '--python', str(self.mcp_script_path),
            '--',
            image_path,
            output_path,
            settings_json
        ]
        
        try:
            print(f"Starting 3D conversion: {image_path}")
            # エンコーディングを明示的に指定
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # エンコーディングエラーを置換文字で処理
                timeout=300
            )
            
            # 出力を表示（デバッグ用）
            print("Blender stdout:", result.stdout)
            if result.stderr:
                print("Blender stderr:", result.stderr)
            
            if result.returncode == 0:
                # 出力ファイルの検証
                if not os.path.exists(output_path):
                    print(f"✗ 出力ファイルが生成されていません: {output_path}")
                    return None
                
                file_size = os.path.getsize(output_path)
                if file_size == 0:
                    print(f"✗ 出力ファイルサイズが0バイトです: {output_path}")
                    return None
                
                # メタデータ生成
                metadata = ConversionMetadata(
                    model_info={
                        "name": Path(output_path).stem,
                        "polygon_count": settings.poly_limit,
                        "texture_size": settings.texture_size,
                        "quality_level": settings.quality,
                        "export_format": settings.export_format
                    },
                    conversion_info={
                        "conversion_time": datetime.now().isoformat(),
                        "original_image": image_path,
                        "settings_used": {
                            "quality": settings.quality,
                            "poly_count_limit": settings.poly_limit,
                            "texture_size": settings.texture_size,
                            "generate_lod": settings.generate_lod,
                            "export_format": settings.export_format
                        }
                    }
                )
                
                # メタデータ保存
                metadata.save(output_path)
                
                print(f"✓ 3D conversion successful: {output_path}")
                return output_path
            else:
                print(f"✗ 3D conversion failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("✗ 3D conversion timed out")
            return None
        except Exception as e:
            print(f"✗ 3D conversion error: {e}")
            return None

class ConversionTester:
    """3D変換テスト"""
    
    def __init__(self):
        self.converter = BlenderMCPConverter()
        self.test_dir = Path("3d_test_output")
        self.test_dir.mkdir(exist_ok=True)
    
    def run_tests(self):
        """各種テストを実行"""
        
        print("=== Blender-MCP 3D変換テスト ===\n")
        
        # テスト画像を作成（実際のテストでは既存画像を使用）
        test_image = self.create_test_image()
        
        # 品質別テスト
        quality_tests = [
            ("低品質", ConversionSettings(quality="low", poly_count_limit=1000)),
            ("中品質", ConversionSettings(quality="medium", poly_count_limit=5000)),
            ("高品質", ConversionSettings(quality="high", poly_count_limit=10000)),
        ]
        
        results = []
        
        for test_name, settings in quality_tests:
            print(f"テスト実行中: {test_name}")
            
            output_file = self.test_dir / f"test_{settings.quality}.{settings.export_format}"
            result = self.converter.convert_to_3d(str(test_image), str(output_file), settings)
            
            if result:
                file_size = os.path.getsize(result) if os.path.exists(result) else 0
                if file_size == 0:
                    print(f"  ✗ 失敗: 出力ファイルサイズが0バイトです")
                    results.append({
                        'name': test_name,
                        'success': False,
                        'file_size': 0,
                        'settings': settings,
                        'error': '出力ファイルサイズが0バイト'
                    })
                else:
                    results.append({
                        'name': test_name,
                        'success': True,
                        'file_size': file_size,
                        'settings': settings
                    })
                    print(f"  ✓ 成功 (ファイルサイズ: {file_size} bytes)")
            else:
                results.append({
                    'name': test_name,
                    'success': False,
                    'settings': settings,
                    'error': '変換処理が失敗'
                })
                print(f"  ✗ 失敗: 変換処理が失敗しました")
            
            print()
        
        # 結果まとめ
        self.print_results(results)
        
        return results
    
    def create_test_image(self) -> Path:
        """テスト用画像を作成"""
        test_image_path = self.test_dir / "test_texture.png"
        
        # 簡単なテスト画像作成（実際の使用では省略可能）
        try:
            from PIL import Image, ImageDraw
            
            img = Image.new('RGB', (512, 512), color='white')
            draw = ImageDraw.Draw(img)
            
            # グラデーション風の模様
            for y in range(512):
                color_value = int(255 * (y / 512))
                draw.line([(0, y), (512, y)], fill=(color_value, 100, 255 - color_value))
            
            img.save(test_image_path)
            print(f"テスト画像作成: {test_image_path}")
            
        except ImportError:
            print("PIL not available, creating dummy image file")
            test_image_path.touch()
        
        return test_image_path
    
    def print_results(self, results):
        """テスト結果を表示"""
        
        print("=== テスト結果まとめ ===")
        print(f"{'テスト名':<15} {'結果':<8} {'ファイルサイズ':<15} {'ポリゴン制限'}")
        print("-" * 60)
        
        for result in results:
            status = "成功" if result['success'] else "失敗"
            size = f"{result.get('file_size', 0):,} bytes" if result['success'] else "-"
            poly_limit = result['settings'].poly_count_limit
            
            print(f"{result['name']:<15} {status:<8} {size:<15} {poly_limit:,}")
        
        success_count = sum(1 for r in results if r['success'])
        print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

# 使用例とテスト実行
def main():
    """メインのテスト実行"""
    
    tester = ConversionTester()
    results = tester.run_tests()
    
    # 成功した場合は次のステップを提案
    if any(r['success'] for r in results):
        print("\n✓ 3D変換の基本機能が確認できました！")
        print("次のステップ:")
        print("1. 実際の生成画像での変換テスト")
        print("2. パイプラインとの統合")
        print("3. バッチ処理の実装")
    else:
        print("\n✗ 3D変換でエラーが発生しています。")
        print("確認項目:")
        print("1. Blenderが正しくインストールされているか")
        print("2. 必要な依存関係が揃っているか")
        print("3. ファイルパスに問題がないか")

if __name__ == "__main__":
    main()