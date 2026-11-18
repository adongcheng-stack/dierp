-- 扩展报价单表，添加产品配置、工艺信息等字段
-- 执行时间：根据实际需要

-- 产品配置信息
ALTER TABLE quotations 
ADD COLUMN IF NOT EXISTS product_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS hdi_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS board_material_brand VARCHAR(100),
ADD COLUMN IF NOT EXISTS board_material_model VARCHAR(100),
ADD COLUMN IF NOT EXISTS board_material_tg VARCHAR(50),
ADD COLUMN IF NOT EXISTS board_material_flame_retardant VARCHAR(50),
ADD COLUMN IF NOT EXISTS board_material_fee VARCHAR(200),
ADD COLUMN IF NOT EXISTS panelization_count INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS output_format VARCHAR(50),
ADD COLUMN IF NOT EXISTS single_piece_length NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS single_piece_width NUMERIC(10, 2),
ADD COLUMN IF NOT EXISTS single_piece_quantity NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS single_piece_unit VARCHAR(20) DEFAULT 'Pcs',
ADD COLUMN IF NOT EXISTS process_border_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS process_border_size NUMERIC(10, 2);

-- 工艺信息
ALTER TABLE quotations 
ADD COLUMN IF NOT EXISTS board_thickness VARCHAR(20),
ADD COLUMN IF NOT EXISTS outer_copper_thickness VARCHAR(20),
ADD COLUMN IF NOT EXISTS inner_copper_thickness VARCHAR(20),
ADD COLUMN IF NOT EXISTS min_line_width_spacing VARCHAR(20),
ADD COLUMN IF NOT EXISTS line_width_spacing_unit VARCHAR(20) DEFAULT 'mil',
ADD COLUMN IF NOT EXISTS min_hole_diameter VARCHAR(20),
ADD COLUMN IF NOT EXISTS hole_diameter_unit VARCHAR(20) DEFAULT 'mm',
ADD COLUMN IF NOT EXISTS solder_mask_color VARCHAR(50),
ADD COLUMN IF NOT EXISTS character_color VARCHAR(50),
ADD COLUMN IF NOT EXISTS solder_mask_coverage VARCHAR(100),
ADD COLUMN IF NOT EXISTS holes_in_pads VARCHAR(50),
ADD COLUMN IF NOT EXISTS surface_finish VARCHAR(100),
ADD COLUMN IF NOT EXISTS lamination_order VARCHAR(100),
ADD COLUMN IF NOT EXISTS impedance VARCHAR(50),
ADD COLUMN IF NOT EXISTS stackup_structure VARCHAR(200),
ADD COLUMN IF NOT EXISTS finger_bevel VARCHAR(50),
ADD COLUMN IF NOT EXISTS half_hole VARCHAR(50),
ADD COLUMN IF NOT EXISTS edge_plating VARCHAR(50),
ADD COLUMN IF NOT EXISTS press_fit_hole VARCHAR(50),
ADD COLUMN IF NOT EXISTS test_method VARCHAR(100);

-- 个性化服务（JSON字段，PostgreSQL使用JSONB，MySQL使用JSON）
-- PostgreSQL
-- ALTER TABLE quotations ADD COLUMN IF NOT EXISTS personalized_services JSONB;
-- MySQL
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS personalized_services JSON;

-- 地址快递信息
ALTER TABLE quotations 
ADD COLUMN IF NOT EXISTS shipping_notification VARCHAR(50),
ADD COLUMN IF NOT EXISTS delivery_note VARCHAR(50),
ADD COLUMN IF NOT EXISTS shipping_address TEXT,
ADD COLUMN IF NOT EXISTS express_company VARCHAR(100);

-- 发票支付信息
ALTER TABLE quotations 
ADD COLUMN IF NOT EXISTS invoice_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS payment_method VARCHAR(100);

-- SMT贴片信息
ALTER TABLE quotations 
ADD COLUMN IF NOT EXISTS smt_patch_required BOOLEAN DEFAULT FALSE;

-- 添加索引（可选，根据查询需求）
-- CREATE INDEX IF NOT EXISTS idx_quotations_product_category ON quotations(product_category);
-- CREATE INDEX IF NOT EXISTS idx_quotations_surface_finish ON quotations(surface_finish);

