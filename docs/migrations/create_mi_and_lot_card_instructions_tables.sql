-- =====================================================
-- 创建 MI指令项表 (mi_instructions) 和 LOT卡指令项表 (lot_card_instructions)
-- 版本: 1.0
-- 日期: 2025-01-XX
-- 说明: 将MI和LOT卡的JSON格式指令内容改为对象表存储
-- =====================================================

-- =====================================================
-- 1. 创建 MI指令项表 (mi_instructions)
-- =====================================================
CREATE TABLE IF NOT EXISTS mi_instructions (
    -- 基础字段（继承自BaseModel）
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 业务字段
    mi_number VARCHAR(50) NOT NULL,
    sequence INTEGER NOT NULL,
    operation_code VARCHAR(50),
    operation_name VARCHAR(200),
    instruction_type VARCHAR(100),
    instruction_content TEXT,
    description VARCHAR(500),
    
    -- 外键约束
    CONSTRAINT fk_mi_instruction_mi 
        FOREIGN KEY (mi_number) 
        REFERENCES mis(mi_number) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    -- 唯一约束：同一MI下序号唯一
    CONSTRAINT uq_mi_instruction_mi_sequence 
        UNIQUE (mi_number, sequence)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_mi_instructions_mi_number 
    ON mi_instructions(mi_number) 
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_mi_instructions_sequence 
    ON mi_instructions(mi_number, sequence) 
    WHERE is_deleted = FALSE;

-- 添加注释
COMMENT ON TABLE mi_instructions IS 'MI指令项表，存储MI的详细指令信息';
COMMENT ON COLUMN mi_instructions.id IS '自增主键';
COMMENT ON COLUMN mi_instructions.mi_number IS 'MI编号（外键）';
COMMENT ON COLUMN mi_instructions.sequence IS '序号（指令的执行顺序）';
COMMENT ON COLUMN mi_instructions.operation_code IS '工序代码（参考工艺路线工序）';
COMMENT ON COLUMN mi_instructions.operation_name IS '工序名称（参考工艺路线工序）';
COMMENT ON COLUMN mi_instructions.instruction_type IS '指令类型，如：开料、钻孔、电镀、线路、阻焊、表面处理、成型等';
COMMENT ON COLUMN mi_instructions.instruction_content IS '指令内容，详细的工序内容描述';
COMMENT ON COLUMN mi_instructions.description IS '说明，对指令的补充说明';
COMMENT ON COLUMN mi_instructions.created_at IS '创建时间';
COMMENT ON COLUMN mi_instructions.updated_at IS '更新时间';
COMMENT ON COLUMN mi_instructions.created_by IS '创建人';
COMMENT ON COLUMN mi_instructions.updated_by IS '更新人';
COMMENT ON COLUMN mi_instructions.is_deleted IS '是否删除（软删除）';

-- =====================================================
-- 2. 创建 LOT卡指令项表 (lot_card_instructions)
-- =====================================================
CREATE TABLE IF NOT EXISTS lot_card_instructions (
    -- 基础字段（继承自BaseModel）
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 业务字段
    lot_number VARCHAR(50) NOT NULL,
    sequence INTEGER NOT NULL,
    operation_code VARCHAR(50),
    operation_name VARCHAR(200),
    instruction_type VARCHAR(100),
    instruction_content TEXT,
    description VARCHAR(500),
    
    -- 外键约束
    CONSTRAINT fk_lot_card_instruction_lot_card 
        FOREIGN KEY (lot_number) 
        REFERENCES lot_cards(lot_number) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    -- 唯一约束：同一LOT卡下序号唯一
    CONSTRAINT uq_lot_card_instruction_lot_sequence 
        UNIQUE (lot_number, sequence)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_lot_card_instructions_lot_number 
    ON lot_card_instructions(lot_number) 
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_lot_card_instructions_sequence 
    ON lot_card_instructions(lot_number, sequence) 
    WHERE is_deleted = FALSE;

-- 添加注释
COMMENT ON TABLE lot_card_instructions IS 'LOT卡指令项表，存储LOT卡的详细指令信息';
COMMENT ON COLUMN lot_card_instructions.id IS '自增主键';
COMMENT ON COLUMN lot_card_instructions.lot_number IS 'LOT卡号（外键）';
COMMENT ON COLUMN lot_card_instructions.sequence IS '序号（指令的执行顺序）';
COMMENT ON COLUMN lot_card_instructions.operation_code IS '工序代码（参考工艺路线工序）';
COMMENT ON COLUMN lot_card_instructions.operation_name IS '工序名称（参考工艺路线工序）';
COMMENT ON COLUMN lot_card_instructions.instruction_type IS '指令类型，如：开料、钻孔、电镀、线路、阻焊、表面处理、成型等';
COMMENT ON COLUMN lot_card_instructions.instruction_content IS '指令内容，详细的工序内容描述';
COMMENT ON COLUMN lot_card_instructions.description IS '说明，对指令的补充说明';
COMMENT ON COLUMN lot_card_instructions.created_at IS '创建时间';
COMMENT ON COLUMN lot_card_instructions.updated_at IS '更新时间';
COMMENT ON COLUMN lot_card_instructions.created_by IS '创建人';
COMMENT ON COLUMN lot_card_instructions.updated_by IS '更新人';
COMMENT ON COLUMN lot_card_instructions.is_deleted IS '是否删除（软删除）';

-- =====================================================
-- 3. 创建更新时间触发器函数（可选，用于自动更新updated_at）
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为mi_instructions表创建触发器
DROP TRIGGER IF EXISTS trigger_update_mi_instructions_updated_at ON mi_instructions;
CREATE TRIGGER trigger_update_mi_instructions_updated_at
    BEFORE UPDATE ON mi_instructions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为lot_card_instructions表创建触发器
DROP TRIGGER IF EXISTS trigger_update_lot_card_instructions_updated_at ON lot_card_instructions;
CREATE TRIGGER trigger_update_lot_card_instructions_updated_at
    BEFORE UPDATE ON lot_card_instructions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 4. 验证表创建成功
-- =====================================================
-- 检查表是否存在
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_name IN ('mi_instructions', 'lot_card_instructions')
ORDER BY table_name;

-- 检查索引
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN ('mi_instructions', 'lot_card_instructions')
ORDER BY tablename, indexname;

-- 检查约束
SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public'
    AND tc.table_name IN ('mi_instructions', 'lot_card_instructions')
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

