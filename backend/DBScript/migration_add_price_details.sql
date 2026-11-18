-- 为报价单表添加价格明细字段
-- PostgreSQL版本

ALTER TABLE quotations 
ADD COLUMN IF NOT EXISTS engineering_fee NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS board_material_fee_amount NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS via_fee NUMERIC(15, 2),
ADD COLUMN IF NOT EXISTS estimated_total_price NUMERIC(15, 2);

-- MySQL版本（如果需要）
-- ALTER TABLE quotations 
-- ADD COLUMN engineering_fee DECIMAL(15, 2),
-- ADD COLUMN board_material_fee_amount DECIMAL(15, 2),
-- ADD COLUMN via_fee DECIMAL(15, 2),
-- ADD COLUMN estimated_total_price DECIMAL(15, 2);

-- 将现有的unit_price值复制到estimated_total_price（如果estimated_total_price为空）
UPDATE quotations 
SET estimated_total_price = unit_price 
WHERE estimated_total_price IS NULL AND unit_price IS NOT NULL;

