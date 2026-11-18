-- =====================================================
-- 简化版：创建 MI指令项表 和 LOT卡指令项表
-- =====================================================

-- 1. 创建 MI指令项表
CREATE TABLE IF NOT EXISTS mi_instructions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    mi_number VARCHAR(50) NOT NULL,
    sequence INTEGER NOT NULL,
    operation_code VARCHAR(50),
    operation_name VARCHAR(200),
    instruction_type VARCHAR(100),
    instruction_content TEXT,
    description VARCHAR(500),
    CONSTRAINT fk_mi_instruction_mi 
        FOREIGN KEY (mi_number) REFERENCES mis(mi_number) ON DELETE CASCADE,
    CONSTRAINT uq_mi_instruction_mi_sequence UNIQUE (mi_number, sequence)
);

CREATE INDEX IF NOT EXISTS idx_mi_instructions_mi_number ON mi_instructions(mi_number) WHERE is_deleted = FALSE;

-- 2. 创建 LOT卡指令项表
CREATE TABLE IF NOT EXISTS lot_card_instructions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    lot_number VARCHAR(50) NOT NULL,
    sequence INTEGER NOT NULL,
    operation_code VARCHAR(50),
    operation_name VARCHAR(200),
    instruction_type VARCHAR(100),
    instruction_content TEXT,
    description VARCHAR(500),
    CONSTRAINT fk_lot_card_instruction_lot_card 
        FOREIGN KEY (lot_number) REFERENCES lot_cards(lot_number) ON DELETE CASCADE,
    CONSTRAINT uq_lot_card_instruction_lot_sequence UNIQUE (lot_number, sequence)
);

CREATE INDEX IF NOT EXISTS idx_lot_card_instructions_lot_number ON lot_card_instructions(lot_number) WHERE is_deleted = FALSE;

