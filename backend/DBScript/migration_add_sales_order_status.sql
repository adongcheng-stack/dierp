-- 添加销售订单状态：已对账(RECONCILED) 和 已关闭(CLOSED)
-- 执行前请备份数据库

-- 添加 RECONCILED 状态
ALTER TYPE salesorderstatus ADD VALUE IF NOT EXISTS 'RECONCILED';

-- 添加 CLOSED 状态
ALTER TYPE salesorderstatus ADD VALUE IF NOT EXISTS 'CLOSED';

