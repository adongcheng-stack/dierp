-- 更新客户状态枚举类型，添加新的审批状态
-- PostgreSQL版本

-- 首先检查枚举类型是否存在新值，如果不存在则添加
DO $$ 
BEGIN
    -- 添加 PENDING_SALES_MANAGER
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PENDING_SALES_MANAGER' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'customerstatus')) THEN
        ALTER TYPE customerstatus ADD VALUE 'PENDING_SALES_MANAGER';
    END IF;
    
    -- 添加 PENDING_FINANCE
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PENDING_FINANCE' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'customerstatus')) THEN
        ALTER TYPE customerstatus ADD VALUE 'PENDING_FINANCE';
    END IF;
    
    -- 添加 PENDING_GENERAL_MANAGER
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'PENDING_GENERAL_MANAGER' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'customerstatus')) THEN
        ALTER TYPE customerstatus ADD VALUE 'PENDING_GENERAL_MANAGER';
    END IF;
    
    -- 添加 FROZEN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'FROZEN' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'customerstatus')) THEN
        ALTER TYPE customerstatus ADD VALUE 'FROZEN';
    END IF;
END $$;

-- 注意：PostgreSQL 的枚举类型一旦创建，不能直接删除值，只能添加新值
-- 如果枚举类型不存在，需要先创建它（通常在表创建时自动创建）
-- 如果枚举类型已经存在但缺少某些值，上面的脚本会添加缺失的值

