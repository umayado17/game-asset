-- =============================================================================
-- GAAAGS (Game Asset Auto-Generation System) Database Schema
-- Version: 1.0
-- Created: 2025/05/27
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. プロジェクト管理テーブル
-- -----------------------------------------------------------------------------

-- プロジェクトマスター
CREATE TABLE projects (
    project_id VARCHAR(36) PRIMARY KEY,  -- UUID
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed, archived
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 統計情報
    total_assets INTEGER DEFAULT 0,
    completed_assets INTEGER DEFAULT 0,
    failed_assets INTEGER DEFAULT 0,
    
    -- 設定情報
    default_quality VARCHAR(20) DEFAULT 'medium', -- low, medium, high
    auto_approve BOOLEAN DEFAULT FALSE,
    
    INDEX idx_projects_status (status),
    INDEX idx_projects_created_at (created_at)
);

-- -----------------------------------------------------------------------------
-- 2. 世界観設定テーブル
-- -----------------------------------------------------------------------------

-- 世界観マスター
CREATE TABLE world_settings (
    world_id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    world_name VARCHAR(255) NOT NULL,
    genre VARCHAR(50) NOT NULL, -- fantasy, sci-fi, modern, horror, etc.
    art_style VARCHAR(50) NOT NULL, -- realistic, cartoon, pixel, anime, etc.
    color_palette VARCHAR(50) NOT NULL, -- dark, bright, vibrant, monochrome, etc.
    theme VARCHAR(50) NOT NULL, -- adventure, horror, peaceful, cyberpunk, etc.
    description TEXT,
    
    -- 詳細設定（JSON形式）
    style_parameters JSON, -- 詳細なスタイル設定
    color_codes JSON, -- 具体的なカラーコード
    reference_images JSON, -- 参考画像のパス
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    INDEX idx_world_settings_project (project_id),
    INDEX idx_world_settings_genre (genre)
);

-- 世界観テンプレート（プリセット）
CREATE TABLE world_templates (
    template_id VARCHAR(36) PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    genre VARCHAR(50) NOT NULL,
    art_style VARCHAR(50) NOT NULL,
    color_palette VARCHAR(50) NOT NULL,
    theme VARCHAR(50) NOT NULL,
    description TEXT,
    default_parameters JSON,
    is_system_template BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_world_templates_genre (genre)
);

-- -----------------------------------------------------------------------------
-- 3. アセット仕様・管理テーブル
-- -----------------------------------------------------------------------------

-- アセットカテゴリマスター
CREATE TABLE asset_categories (
    category_id VARCHAR(36) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id VARCHAR(36), -- 階層構造対応
    description TEXT,
    default_tags JSON,
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_category_id) REFERENCES asset_categories(category_id),
    INDEX idx_asset_categories_parent (parent_category_id)
);

-- アセット仕様テーブル
CREATE TABLE asset_specifications (
    spec_id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    world_id VARCHAR(36) NOT NULL,
    asset_name VARCHAR(255) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 3, -- 1(低) - 5(高)
    tags JSON, -- タグのJSON配列
    
    -- 生成設定
    generation_settings JSON, -- 生成時の詳細設定
    custom_prompt TEXT, -- カスタムプロンプト
    reference_images JSON, -- 参考画像
    
    -- ステータス
    status VARCHAR(20) DEFAULT 'pending', -- pending, generating, completed, failed, cancelled
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (world_id) REFERENCES world_settings(world_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES asset_categories(category_id),
    
    INDEX idx_asset_specs_project (project_id),
    INDEX idx_asset_specs_world (world_id),
    INDEX idx_asset_specs_status (status),
    INDEX idx_asset_specs_priority (priority)
);

-- 生成されたアセットテーブル
CREATE TABLE generated_assets (
    asset_id VARCHAR(36) PRIMARY KEY,
    spec_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL,
    world_id VARCHAR(36) NOT NULL,
    
    -- ファイル情報
    asset_name VARCHAR(255) NOT NULL,
    file_path_2d VARCHAR(500), -- 2D画像パス
    file_path_3d VARCHAR(500), -- 3Dモデルパス
    file_size_2d BIGINT, -- 2Dファイルサイズ（bytes）
    file_size_3d BIGINT, -- 3Dファイルサイズ（bytes）
    
    -- 生成情報
    generation_method VARCHAR(50), -- gemini, imagen3, etc.
    prompt_used TEXT NOT NULL,
    generation_parameters JSON,
    
    -- 品質情報
    quality_score DECIMAL(3,2), -- 0.00-5.00
    auto_quality_check JSON, -- 自動品質チェック結果
    manual_review_status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, needs_revision
    manual_review_notes TEXT,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    
    -- 3D変換情報
    conversion_status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    conversion_settings JSON,
    polygon_count INTEGER,
    texture_resolution VARCHAR(20),
    
    -- ステータス・履歴
    status VARCHAR(20) DEFAULT 'generated', -- generated, approved, rejected, archived
    version INTEGER DEFAULT 1,
    parent_asset_id VARCHAR(36), -- 再生成時の元アセット
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (spec_id) REFERENCES asset_specifications(spec_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (world_id) REFERENCES world_settings(world_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_asset_id) REFERENCES generated_assets(asset_id),
    
    INDEX idx_generated_assets_spec (spec_id),
    INDEX idx_generated_assets_project (project_id),
    INDEX idx_generated_assets_status (status),
    INDEX idx_generated_assets_review (manual_review_status),
    INDEX idx_generated_assets_conversion (conversion_status),
    INDEX idx_generated_assets_created (created_at)
);

-- -----------------------------------------------------------------------------
-- 4. 生成プロセス・履歴管理テーブル
-- -----------------------------------------------------------------------------

-- 生成ジョブテーブル
CREATE TABLE generation_jobs (
    job_id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    job_name VARCHAR(255),
    job_type VARCHAR(50) NOT NULL, -- batch_generation, single_asset, 3d_conversion
    
    -- ジョブ設定
    target_specs JSON, -- 対象のspec_idリスト
    batch_settings JSON,
    
    -- 進捗情報
    status VARCHAR(20) DEFAULT 'queued', -- queued, running, completed, failed, cancelled
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    
    -- 実行情報
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_completion TIMESTAMP,
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    
    INDEX idx_generation_jobs_project (project_id),
    INDEX idx_generation_jobs_status (status),
    INDEX idx_generation_jobs_created (created_at)
);

-- 生成履歴テーブル
CREATE TABLE generation_history (
    history_id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36),
    asset_id VARCHAR(36),
    spec_id VARCHAR(36) NOT NULL,
    
    -- アクション情報
    action_type VARCHAR(50) NOT NULL, -- generate_2d, convert_3d, approve, reject, regenerate
    action_status VARCHAR(20) NOT NULL, -- success, failed, cancelled
    
    -- 詳細情報
    input_parameters JSON,
    output_results JSON,
    error_details JSON,
    execution_time_seconds INTEGER,
    
    -- API使用情報
    api_provider VARCHAR(50), -- gemini, imagen3, blender
    api_cost DECIMAL(10,4), -- API使用コスト
    api_response_time_ms INTEGER,
    
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES generation_jobs(job_id) ON DELETE SET NULL,
    FOREIGN KEY (asset_id) REFERENCES generated_assets(asset_id) ON DELETE CASCADE,
    FOREIGN KEY (spec_id) REFERENCES asset_specifications(spec_id) ON DELETE CASCADE,
    
    INDEX idx_generation_history_job (job_id),
    INDEX idx_generation_history_asset (asset_id),
    INDEX idx_generation_history_action (action_type),
    INDEX idx_generation_history_performed (performed_at)
);

-- -----------------------------------------------------------------------------
-- 5. プロンプト・テンプレート管理テーブル
-- -----------------------------------------------------------------------------

-- プロンプトテンプレートテーブル
CREATE TABLE prompt_templates (
    template_id VARCHAR(36) PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- character, environment, item, weapon, etc.
    
    -- テンプレート内容
    base_prompt TEXT NOT NULL,
    style_modifiers JSON, -- スタイル別の修飾子
    quality_enhancers JSON, -- 品質向上用の追加プロンプト
    
    -- 適用条件
    applicable_genres JSON, -- 適用可能なジャンル
    applicable_styles JSON, -- 適用可能なアートスタイル
    
    -- 統計情報
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2), -- 成功率（%）
    avg_quality_score DECIMAL(3,2),
    
    is_system_template BOOLEAN DEFAULT FALSE,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_prompt_templates_category (category),
    INDEX idx_prompt_templates_usage (usage_count DESC)
);

-- 生成されたプロンプト履歴
CREATE TABLE generated_prompts (
    prompt_id VARCHAR(36) PRIMARY KEY,
    asset_id VARCHAR(36) NOT NULL,
    template_id VARCHAR(36),
    
    -- プロンプト内容
    final_prompt TEXT NOT NULL,
    prompt_components JSON, -- プロンプトの構成要素
    
    -- 生成設定
    llm_model VARCHAR(50), -- gemini-2.0-flash-exp, etc.
    generation_parameters JSON,
    
    -- 評価情報
    effectiveness_score DECIMAL(3,2), -- プロンプトの効果スコア
    feedback_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (asset_id) REFERENCES generated_assets(asset_id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES prompt_templates(template_id) ON DELETE SET NULL,
    
    INDEX idx_generated_prompts_asset (asset_id),
    INDEX idx_generated_prompts_template (template_id)
);

-- -----------------------------------------------------------------------------
-- 6. 品質管理・評価テーブル
-- -----------------------------------------------------------------------------

-- 品質評価基準テーブル
CREATE TABLE quality_criteria (
    criteria_id VARCHAR(36) PRIMARY KEY,
    criteria_name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- technical, artistic, consistency, usability
    description TEXT,
    weight DECIMAL(3,2) DEFAULT 1.00, -- 評価の重み
    evaluation_method VARCHAR(50), -- auto, manual, hybrid
    
    -- 自動評価設定
    auto_check_script TEXT,
    threshold_values JSON,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_quality_criteria_category (category)
);

-- 品質評価結果テーブル
CREATE TABLE quality_evaluations (
    evaluation_id VARCHAR(36) PRIMARY KEY,
    asset_id VARCHAR(36) NOT NULL,
    criteria_id VARCHAR(36) NOT NULL,
    
    -- 評価結果
    score DECIMAL(3,2) NOT NULL, -- 0.00-5.00
    evaluation_method VARCHAR(20), -- auto, manual
    evaluator VARCHAR(100), -- 評価者（人間の場合）
    
    -- 詳細情報
    evaluation_details JSON,
    improvement_suggestions TEXT,
    
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (asset_id) REFERENCES generated_assets(asset_id) ON DELETE CASCADE,
    FOREIGN KEY (criteria_id) REFERENCES quality_criteria(criteria_id),
    
    PRIMARY KEY (evaluation_id),
    UNIQUE KEY uk_evaluation_asset_criteria (asset_id, criteria_id),
    
    INDEX idx_quality_evaluations_asset (asset_id),
    INDEX idx_quality_evaluations_score (score)
);

-- -----------------------------------------------------------------------------
-- 7. システム設定・ユーザー管理テーブル
-- -----------------------------------------------------------------------------

-- システム設定テーブル
CREATE TABLE system_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string', -- string, integer, boolean, json
    category VARCHAR(50), -- api, performance, quality, ui
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_system_settings_category (category)
);

-- API使用統計テーブル
CREATE TABLE api_usage_stats (
    stats_id VARCHAR(36) PRIMARY KEY,
    api_provider VARCHAR(50) NOT NULL,
    date_recorded DATE NOT NULL,
    
    -- 使用量統計
    requests_count INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0.00,
    
    -- 性能統計
    avg_response_time_ms INTEGER,
    min_response_time_ms INTEGER,
    max_response_time_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_api_stats_provider_date (api_provider, date_recorded),
    INDEX idx_api_stats_date (date_recorded)
);

-- -----------------------------------------------------------------------------
-- 8. 初期データ投入
-- -----------------------------------------------------------------------------

-- デフォルトアセットカテゴリ
INSERT INTO asset_categories (category_id, category_name, description, sort_order) VALUES
('cat-001', 'Characters', 'キャラクター（人間、動物、モンスターなど）', 1),
('cat-002', 'Environments', '環境・背景（建物、地形、風景など）', 2),
('cat-003', 'Items', 'アイテム（道具、宝物、消耗品など）', 3),
('cat-004', 'Weapons', '武器（剣、銃、魔法の杖など）', 4),
('cat-005', 'Vehicles', '乗り物（車、船、宇宙船など）', 5),
('cat-006', 'UI Elements', 'UIエレメント（ボタン、アイコンなど）', 6);

-- キャラクターサブカテゴリ
INSERT INTO asset_categories (category_id, category_name, parent_category_id, description, sort_order) VALUES
('cat-001-001', 'Heroes', 'cat-001', '主人公・ヒーロー', 1),
('cat-001-002', 'NPCs', 'cat-001', 'ノンプレイヤーキャラクター', 2),
('cat-001-003', 'Enemies', 'cat-001', '敵キャラクター', 3),
('cat-001-004', 'Animals', 'cat-001', '動物', 4);

-- 世界観テンプレート
INSERT INTO world_templates (template_id, template_name, genre, art_style, color_palette, theme, description) VALUES
('tmpl-001', 'Medieval Fantasy', 'fantasy', 'realistic', 'warm', 'adventure', '中世ファンタジーの世界観'),
('tmpl-002', 'Sci-Fi Space', 'sci-fi', 'realistic', 'cool', 'adventure', '宇宙を舞台にしたSF世界'),
('tmpl-003', 'Cartoon Adventure', 'fantasy', 'cartoon', 'bright', 'adventure', 'カラフルなカートゥーン世界'),
('tmpl-004', 'Cyberpunk City', 'sci-fi', 'realistic', 'neon', 'cyberpunk', 'サイバーパンクな未来都市'),
('tmpl-005', 'Pixel Retro', 'fantasy', 'pixel', 'retro', 'adventure', 'レトロなピクセルアート風');

-- 品質評価基準
INSERT INTO quality_criteria (criteria_id, criteria_name, category, description, weight) VALUES
('qc-001', 'Technical Quality', 'technical', '技術的品質（解像度、ノイズ、歪みなど）', 1.00),
('qc-002', 'Style Consistency', 'artistic', 'スタイルの一貫性', 1.20),
('qc-003', 'World Coherence', 'consistency', '世界観との整合性', 1.10),
('qc-004', 'Game Usability', 'usability', 'ゲームでの使用適性', 0.90),
('qc-005', 'Visual Appeal', 'artistic', '視覚的魅力', 0.80);

-- システム初期設定
INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description) VALUES
('api.gemini.key', '', 'string', 'api', 'Gemini APIキー'),
('api.gemini.model', 'gemini-2.0-flash-exp', 'string', 'api', '使用するGeminiモデル'),
('api.max_concurrent_requests', '5', 'integer', 'performance', 'API同時リクエスト数'),
('quality.auto_approve_threshold', '4.0', 'string', 'quality', '自動承認の品質しきい値'),
('generation.default_image_size', '1024', 'integer', 'generation', 'デフォルト画像サイズ'),
('3d.default_poly_limit', '5000', 'integer', '3d', 'デフォルトポリゴン数制限'),
('3d.blender_path', '', 'string', '3d', 'Blenderの実行ファイルパス'),
('storage.max_file_size_mb', '50', 'integer', 'storage', '最大ファイルサイズ（MB）');

-- -----------------------------------------------------------------------------
-- 9. インデックス最適化とパフォーマンス
-- -----------------------------------------------------------------------------

-- 複合インデックス（よく使用される検索パターン用）
CREATE INDEX idx_assets_project_status ON generated_assets(project_id, status);
CREATE INDEX idx_assets_world_category ON generated_assets(world_id, spec_id);
CREATE INDEX idx_history_asset_action ON generation_history(asset_id, action_type, performed_at);
CREATE INDEX idx_jobs_project_status_created ON generation_jobs(project_id, status, created_at);

-- フルテキスト検索インデックス（MySQL/PostgreSQL用）
-- CREATE FULLTEXT INDEX idx_assets_description ON asset_specifications(description);
-- CREATE FULLTEXT INDEX idx_prompts_content ON generated_prompts(final_prompt);

-- -----------------------------------------------------------------------------
-- 10. ビュー定義（よく使用されるクエリの簡略化）
-- -----------------------------------------------------------------------------

-- プロジェクト統計ビュー
CREATE VIEW v_project_stats AS
SELECT 
    p.project_id,
    p.project_name,
    p.status as project_status,
    COUNT(DISTINCT ws.world_id) as world_count,
    COUNT(DISTINCT spec.spec_id) as total_specs,
    COUNT(DISTINCT CASE WHEN ga.status = 'approved' THEN ga.asset_id END) as approved_assets,
    COUNT(DISTINCT CASE WHEN ga.status = 'generated' THEN ga.asset_id END) as pending_assets,
    COUNT(DISTINCT CASE WHEN ga.status = 'rejected' THEN ga.asset_id END) as rejected_assets,
    AVG(ga.quality_score) as avg_quality_score,
    p.created_at,
    p.updated_at
FROM projects p
LEFT JOIN world_settings ws ON p.project_id = ws.project_id
LEFT JOIN asset_specifications spec ON p.project_id = spec.project_id
LEFT JOIN generated_assets ga ON spec.spec_id = ga.spec_id
GROUP BY p.project_id, p.project_name, p.status, p.created_at, p.updated_at;

-- アセット詳細ビュー
CREATE VIEW v_asset_details AS
SELECT 
    ga.asset_id,
    ga.asset_name,
    p.project_name,
    ws.world_name,
    ac.category_name,
    ga.status,
    ga.manual_review_status,
    ga.quality_score,
    ga.polygon_count,
    ga.file_size_2d,
    ga.file_size_3d,
    ga.created_at,
    spec.priority,
    spec.description as spec_description
FROM generated_assets ga
JOIN asset_specifications spec ON ga.spec_id = spec.spec_id
JOIN projects p ON ga.project_id = p.project_id
JOIN world_settings ws ON ga.world_id = ws.world_id
JOIN asset_categories ac ON spec.category_id = ac.category_id;

-- API使用量サマリービュー
CREATE VIEW v_api_usage_summary AS
SELECT 
    api_provider,
    SUM(requests_count) as total_requests,
    SUM(successful_requests) as total_successful,
    SUM(failed_requests) as total_failed,
    SUM(total_cost) as total_cost,
    AVG(avg_response_time_ms) as avg_response_time,
    MAX(date_recorded) as latest_date
FROM api_usage_stats
GROUP BY api_provider;

-- -----------------------------------------------------------------------------
-- 11. トリガー定義（データ整合性とログ記録）
-- -----------------------------------------------------------------------------

-- プロジェクト統計更新トリガー（概念的な定義、実装は環境依存）
/*
DELIMITER //
CREATE TRIGGER tr_update_project_stats_after_asset_change
AFTER UPDATE ON generated_assets
FOR EACH ROW
BEGIN
    UPDATE projects SET 
        completed_assets = (
            SELECT COUNT(*) FROM generated_assets 
            WHERE project_id = NEW.project_id AND status = 'approved'
        ),
        failed_assets = (
            SELECT COUNT(*) FROM generated_assets 
            WHERE project_id = NEW.project_id AND status = 'rejected'
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE project_id = NEW.project_id;
END//
DELIMITER ;
*/