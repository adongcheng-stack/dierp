-- 扩展 BOM 与工艺路线表，新增字段以匹配前端/需求
-- 请在执行前备份数据库

-- BOM 表新增字段
ALTER TABLE boms
    ADD COLUMN IF NOT EXISTS plant_id VARCHAR(50),
    ADD COLUMN IF NOT EXISTS bom_type VARCHAR(20) DEFAULT 'PRODUCTION',
    ADD COLUMN IF NOT EXISTS base_quantity NUMERIC(15,4) DEFAULT 1,
    ADD COLUMN IF NOT EXISTS base_uom VARCHAR(20) DEFAULT 'PNL';

-- BOM 明细新增字段
ALTER TABLE bom_items
    ADD COLUMN IF NOT EXISTS item_category VARCHAR(50),
    ADD COLUMN IF NOT EXISTS scrap_rate NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS calculation_formula VARCHAR(100),
    ADD COLUMN IF NOT EXISTS layer_code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS material_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS process_step VARCHAR(50);

-- 工艺路线工序新增字段
ALTER TABLE routing_operations
    ADD COLUMN IF NOT EXISTS sop_link VARCHAR(255),
    ADD COLUMN IF NOT EXISTS needs_reporting BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS auto_deduct_material BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS trigger_quality_check BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS estimated_currency VARCHAR(10),
    ADD COLUMN IF NOT EXISTS inspection_plan_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS sampling_rate NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS verification_logic VARCHAR(50);


