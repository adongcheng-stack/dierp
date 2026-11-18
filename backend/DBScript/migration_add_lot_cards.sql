-- 创建LOT卡表
CREATE TABLE IF NOT EXISTS lot_cards (
    id SERIAL PRIMARY KEY,
    lot_number VARCHAR(50) UNIQUE NOT NULL,
    production_order_number VARCHAR(50) NOT NULL,
    mi_number VARCHAR(50) NOT NULL,
    material_code VARCHAR(50) NOT NULL,
    quantity NUMERIC(15, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    mi_content TEXT,
    completed_at TIMESTAMP,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    FOREIGN KEY (production_order_number) REFERENCES production_orders(order_number),
    FOREIGN KEY (mi_number) REFERENCES mis(mi_number),
    FOREIGN KEY (material_code) REFERENCES materials(material_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_lot_card_production_order ON lot_cards(production_order_number);
CREATE INDEX IF NOT EXISTS idx_lot_card_mi ON lot_cards(mi_number);
CREATE INDEX IF NOT EXISTS idx_lot_card_material ON lot_cards(material_code);
CREATE INDEX IF NOT EXISTS idx_lot_card_status ON lot_cards(status);
CREATE INDEX IF NOT EXISTS idx_lot_card_lot_number ON lot_cards(lot_number);

-- 添加注释
COMMENT ON TABLE lot_cards IS 'LOT卡表，由MI自动生成，用于工时报工';
COMMENT ON COLUMN lot_cards.lot_number IS 'LOT卡号，唯一标识';
COMMENT ON COLUMN lot_cards.production_order_number IS '生产订单号';
COMMENT ON COLUMN lot_cards.mi_number IS 'MI编号';
COMMENT ON COLUMN lot_cards.material_code IS '物料编码';
COMMENT ON COLUMN lot_cards.quantity IS '数量';
COMMENT ON COLUMN lot_cards.unit IS '单位';
COMMENT ON COLUMN lot_cards.status IS '状态：ACTIVE, COMPLETED, CANCELLED';
COMMENT ON COLUMN lot_cards.mi_content IS 'MI内容（JSON格式，从MI复制）';
COMMENT ON COLUMN lot_cards.completed_at IS '完成时间';
COMMENT ON COLUMN lot_cards.remarks IS '备注';
