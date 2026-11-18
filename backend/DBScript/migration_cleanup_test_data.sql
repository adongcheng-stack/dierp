-- =====================================================
-- 清理测试数据SQL脚本
-- 说明：此脚本用于清理所有测试数据，但保留users表
-- 注意：执行前请备份数据库！
-- =====================================================

-- 禁用外键检查（PostgreSQL）
SET session_replication_role = 'replica';

-- 或者对于MySQL，使用：
-- SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 删除生产计划与控制(PP)模块数据
-- =====================================================

-- 删除工序报工表（依赖生产订单和工作中心）
DELETE FROM operation_reports;

-- 删除生产进度表（依赖生产订单）
DELETE FROM production_progress;

-- 删除生产订单表（依赖销售订单、物料、生产版本）
DELETE FROM production_orders;

-- 删除工作中心表（自引用，先删除子节点）
-- 注意：如果有自引用关系，需要先删除子节点
DELETE FROM work_centers WHERE parent_work_center_id IS NOT NULL;
DELETE FROM work_centers;

-- =====================================================
-- 2. 删除物料管理(MM)模块数据
-- =====================================================

-- 删除物料事务表（依赖物料）
DELETE FROM material_transactions;

-- 删除生产领料表（依赖物料和生产订单）
DELETE FROM material_issues;

-- 删除物料表（依赖BOM、工艺路线等）
DELETE FROM materials;

-- =====================================================
-- 3. 删除工程管理(ENG)模块数据
-- =====================================================

-- 删除生产版本表（依赖物料、BOM、工艺路线、MI）
DELETE FROM production_versions;

-- 删除MI表（依赖物料）
DELETE FROM mis;

-- 删除工艺路线工序表（依赖工艺路线和工作中心）
DELETE FROM routing_operations;

-- 删除工艺路线表（依赖物料）
DELETE FROM routings;

-- 删除BOM明细表（依赖BOM和物料）
DELETE FROM bom_items;

-- 删除BOM表（依赖物料）
DELETE FROM boms;

-- =====================================================
-- 4. 删除销售与分销(SD)模块数据
-- =====================================================

-- 删除合同评审表（依赖销售订单）
DELETE FROM contract_reviews;

-- 删除销售订单表（依赖报价单、客户、物料、生产版本）
DELETE FROM sales_orders;

-- 删除报价单明细表（依赖报价单）
DELETE FROM quotation_items;

-- 删除报价单表（依赖客户）
DELETE FROM quotations;

-- 删除本厂编号映射表（依赖客户、物料、生产版本）
DELETE FROM factory_product_mappings;

-- 删除客户销售数据表（依赖客户）
DELETE FROM customer_sales_data;

-- 删除客户合作属性表（依赖客户）
DELETE FROM customer_partner_functions;

-- 删除客户联系人表（依赖客户）
DELETE FROM customer_contacts;

-- 删除客户地址表（依赖客户）
DELETE FROM customer_addresses;

-- 删除客户表
DELETE FROM customers;

-- =====================================================
-- 5. 重置序列（PostgreSQL，如果需要）
-- =====================================================
-- 注意：如果使用了自增ID，可能需要重置序列
-- 例如：ALTER SEQUENCE customers_id_seq RESTART WITH 1;

-- =====================================================
-- 恢复外键检查
-- =====================================================

-- PostgreSQL
SET session_replication_role = 'origin';

-- MySQL
-- SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- 清理完成
-- =====================================================
-- 注意：users表未被删除，所有用户数据保留

