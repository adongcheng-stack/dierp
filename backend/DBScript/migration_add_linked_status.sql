-- 更新报价单状态枚举类型，添加 LINKED 状态
-- 执行方法：在 PostgreSQL 中直接执行此 SQL 命令

-- 检查 LINKED 是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'LINKED' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'quotationstatus')
    ) THEN
        -- 添加 LINKED 到枚举类型
        ALTER TYPE quotationstatus ADD VALUE 'LINKED';
        RAISE NOTICE 'Successfully added LINKED status to quotationstatus enum type';
    ELSE
        RAISE NOTICE 'LINKED status already exists, no need to add';
    END IF;
END $$;

