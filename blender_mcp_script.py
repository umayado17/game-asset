
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
