-- 扩展工艺路线表，添加审计追踪字段
ALTER TABLE routings ADD COLUMN IF NOT EXISTS change_request_no VARCHAR(50);

-- 扩展工艺路线工序表，添加外协采购申请字段
ALTER TABLE routing_operations ADD COLUMN IF NOT EXISTS generate_purchase_req BOOLEAN DEFAULT FALSE;

