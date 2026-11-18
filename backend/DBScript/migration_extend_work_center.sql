-- 扩展 work_centers 表字段，执行前请备份

ALTER TABLE work_centers
    ADD COLUMN IF NOT EXISTS control_key VARCHAR(50),
    ADD COLUMN IF NOT EXISTS capacity_formula_setup VARCHAR(50),
    ADD COLUMN IF NOT EXISTS capacity_formula_processing VARCHAR(50),
    ADD COLUMN IF NOT EXISTS capacity_formula_teardown VARCHAR(50),
    ADD COLUMN IF NOT EXISTS activity_types TEXT;


