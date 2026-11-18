-- 创建本厂编号映射表
CREATE TABLE IF NOT EXISTS factory_product_mappings (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    factory_product_number VARCHAR(50) NOT NULL,
    material_code VARCHAR(50) NOT NULL REFERENCES materials(material_code),
    production_version_id VARCHAR(50) REFERENCES production_versions(production_version_id),
    is_default BOOLEAN DEFAULT TRUE,
    effective_date TIMESTAMP NOT NULL,
    expiry_date TIMESTAMP,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- 唯一约束：同一客户的本厂编号在同一时间段内唯一
    CONSTRAINT uq_factory_product UNIQUE (customer_id, factory_product_number, effective_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_factory_product_mapping_customer ON factory_product_mappings(customer_id);
CREATE INDEX IF NOT EXISTS idx_factory_product_mapping_product ON factory_product_mappings(factory_product_number);
CREATE INDEX IF NOT EXISTS idx_factory_product_mapping_material ON factory_product_mappings(material_code);
CREATE INDEX IF NOT EXISTS idx_factory_product_mapping_version ON factory_product_mappings(production_version_id);

-- 增强销售订单表
ALTER TABLE sales_orders 
    ADD COLUMN IF NOT EXISTS material_code VARCHAR(50) REFERENCES materials(material_code),
    ADD COLUMN IF NOT EXISTS production_version_id VARCHAR(50) REFERENCES production_versions(production_version_id),
    ADD COLUMN IF NOT EXISTS sales_unit VARCHAR(20),
    ADD COLUMN IF NOT EXISTS production_quantity NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS production_unit VARCHAR(20),
    ADD COLUMN IF NOT EXISTS conversion_factor NUMERIC(15, 4);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sales_order_material ON sales_orders(material_code);
CREATE INDEX IF NOT EXISTS idx_sales_order_production_version ON sales_orders(production_version_id);

-- 增强生产订单表
ALTER TABLE production_orders
    ADD COLUMN IF NOT EXISTS sales_quantity NUMERIC(15, 2),
    ADD COLUMN IF NOT EXISTS sales_unit VARCHAR(20),
    ADD COLUMN IF NOT EXISTS conversion_factor NUMERIC(15, 4);

-- 创建索引（如果还没有）
CREATE INDEX IF NOT EXISTS idx_production_order_sales ON production_orders(sales_order_number);
CREATE INDEX IF NOT EXISTS idx_production_order_material ON production_orders(material_code);
CREATE INDEX IF NOT EXISTS idx_production_order_version ON production_orders(production_version_id);

