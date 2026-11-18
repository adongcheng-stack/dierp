-- 更新生产版本表，使 mi_number 字段可为空
-- 执行方法：在 PostgreSQL 中直接执行此 SQL 命令

-- 修改 mi_number 字段为可空
ALTER TABLE production_versions 
ALTER COLUMN mi_number DROP NOT NULL;

-- 验证修改
SELECT 
    column_name, 
    is_nullable, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'production_versions' 
AND column_name = 'mi_number';

