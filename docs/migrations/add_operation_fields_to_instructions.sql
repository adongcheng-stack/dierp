-- =====================================================
-- 为MI指令项表和LOT卡指令项表添加工序代码和工序名称字段
-- 版本: 1.1
-- 日期: 2025-01-XX
-- 说明: 参考工艺路线工序，添加operation_code和operation_name字段
-- =====================================================

-- =====================================================
-- 1. 为 mi_instructions 表添加字段
-- =====================================================
ALTER TABLE mi_instructions 
ADD COLUMN IF NOT EXISTS operation_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS operation_name VARCHAR(200);

-- 添加注释
COMMENT ON COLUMN mi_instructions.operation_code IS '工序代码（参考工艺路线工序）';
COMMENT ON COLUMN mi_instructions.operation_name IS '工序名称（参考工艺路线工序）';

-- =====================================================
-- 2. 为 lot_card_instructions 表添加字段
-- =====================================================
ALTER TABLE lot_card_instructions 
ADD COLUMN IF NOT EXISTS operation_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS operation_name VARCHAR(200);

-- 添加注释
COMMENT ON COLUMN lot_card_instructions.operation_code IS '工序代码（参考工艺路线工序）';
COMMENT ON COLUMN lot_card_instructions.operation_name IS '工序名称（参考工艺路线工序）';

-- =====================================================
-- 3. 验证字段添加成功
-- =====================================================
-- 检查字段
SELECT 
    table_name,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name IN ('mi_instructions', 'lot_card_instructions')
    AND column_name IN ('operation_code', 'operation_name')
ORDER BY table_name, column_name;

