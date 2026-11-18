"""
数据迁移脚本：为现有客户创建本厂编号映射

此脚本会：
1. 从现有的销售订单中提取客户ID和产品编号
2. 尝试从销售订单中获取material_code和production_version_id（如果已存在）
3. 如果没有，尝试从报价单中获取物料信息
4. 创建本厂编号映射记录

使用方法：
python backend/migration_create_factory_product_mappings.py
"""

import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hserp")

def create_mappings():
    """创建本厂编号映射"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        print("开始数据迁移：创建本厂编号映射...")
        
        # 1. 从销售订单中提取唯一的客户ID和产品编号组合
        print("\n步骤1: 从销售订单中提取客户和产品信息...")
        sales_orders_query = text("""
            SELECT DISTINCT 
                customer_id,
                product_number,
                material_code,
                production_version_id
            FROM sales_orders
            WHERE customer_id IS NOT NULL 
                AND product_number IS NOT NULL
                AND is_deleted = FALSE
        """)
        
        sales_orders = db.execute(sales_orders_query).fetchall()
        print(f"找到 {len(sales_orders)} 个唯一的客户-产品组合")
        
        # 2. 从报价单中提取客户和产品信息（作为补充）
        print("\n步骤2: 从报价单中提取客户和产品信息...")
        quotations_query = text("""
            SELECT DISTINCT 
                q.customer_id,
                qi.material_code,
                q.product_number
            FROM quotations q
            INNER JOIN quotation_items qi ON q.quotation_number = qi.quotation_number
            WHERE q.customer_id IS NOT NULL 
                AND q.product_number IS NOT NULL
                AND q.is_deleted = FALSE
        """)
        
        quotations = db.execute(quotations_query).fetchall()
        print(f"找到 {len(quotations)} 个报价单中的客户-产品组合")
        
        # 3. 合并数据并创建映射
        print("\n步骤3: 创建本厂编号映射...")
        
        created_count = 0
        skipped_count = 0
        
        # 处理销售订单数据
        for so in sales_orders:
            customer_id = so[0]
            product_number = so[1]  # 这是本厂编号
            material_code = so[2]
            production_version_id = so[3]
            
            # 检查是否已存在映射
            check_query = text("""
                SELECT id FROM factory_product_mappings
                WHERE customer_id = :customer_id
                    AND factory_product_number = :product_number
                    AND is_deleted = FALSE
            """)
            existing = db.execute(
                check_query,
                {"customer_id": customer_id, "product_number": product_number}
            ).first()
            
            if existing:
                print(f"  跳过：客户 {customer_id} 的产品 {product_number} 已存在映射")
                skipped_count += 1
                continue
            
            # 如果没有material_code，尝试从报价单中查找
            if not material_code:
                for qt in quotations:
                    if qt[0] == customer_id and qt[2] == product_number:
                        material_code = qt[1]
                        break
            
            # 如果仍然没有material_code，跳过
            if not material_code:
                print(f"  警告：客户 {customer_id} 的产品 {product_number} 没有物料编码，跳过")
                skipped_count += 1
                continue
            
            # 验证物料是否存在
            material_check = text("SELECT material_code FROM materials WHERE material_code = :material_code")
            material_exists = db.execute(material_check, {"material_code": material_code}).first()
            if not material_exists:
                print(f"  警告：物料 {material_code} 不存在，跳过")
                skipped_count += 1
                continue
            
            # 验证生产版本（如果提供）
            if production_version_id:
                version_check = text("""
                    SELECT production_version_id FROM production_versions 
                    WHERE production_version_id = :version_id
                """)
                version_exists = db.execute(version_check, {"version_id": production_version_id}).first()
                if not version_exists:
                    print(f"  警告：生产版本 {production_version_id} 不存在，将不设置生产版本")
                    production_version_id = None
            
            # 创建映射
            insert_query = text("""
                INSERT INTO factory_product_mappings (
                    customer_id,
                    factory_product_number,
                    material_code,
                    production_version_id,
                    is_default,
                    effective_date,
                    created_by,
                    created_at,
                    updated_at
                ) VALUES (
                    :customer_id,
                    :product_number,
                    :material_code,
                    :production_version_id,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    'system_migration',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
            """)
            
            db.execute(
                insert_query,
                {
                    "customer_id": customer_id,
                    "product_number": product_number,
                    "material_code": material_code,
                    "production_version_id": production_version_id
                }
            )
            created_count += 1
            print(f"  ✓ 创建映射：客户 {customer_id}，产品 {product_number} -> 物料 {material_code}")
        
        # 处理报价单数据（补充销售订单中没有的）
        quotation_mappings = {}
        for qt in quotations:
            customer_id = qt[0]
            material_code = qt[1]
            product_number = qt[2]
            
            key = (customer_id, product_number)
            if key not in quotation_mappings:
                quotation_mappings[key] = material_code
        
        for (customer_id, product_number), material_code in quotation_mappings.items():
            # 检查是否已存在映射
            check_query = text("""
                SELECT id FROM factory_product_mappings
                WHERE customer_id = :customer_id
                    AND factory_product_number = :product_number
                    AND is_deleted = FALSE
            """)
            existing = db.execute(
                check_query,
                {"customer_id": customer_id, "product_number": product_number}
            ).first()
            
            if existing:
                continue
            
            # 验证物料是否存在
            material_check = text("SELECT material_code FROM materials WHERE material_code = :material_code")
            material_exists = db.execute(material_check, {"material_code": material_code}).first()
            if not material_exists:
                continue
            
            # 创建映射
            insert_query = text("""
                INSERT INTO factory_product_mappings (
                    customer_id,
                    factory_product_number,
                    material_code,
                    production_version_id,
                    is_default,
                    effective_date,
                    created_by,
                    created_at,
                    updated_at
                ) VALUES (
                    :customer_id,
                    :product_number,
                    :material_code,
                    NULL,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    'system_migration',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
            """)
            
            db.execute(
                insert_query,
                {
                    "customer_id": customer_id,
                    "product_number": product_number,
                    "material_code": material_code,
                }
            )
            created_count += 1
            print(f"  ✓ 创建映射（来自报价单）：客户 {customer_id}，产品 {product_number} -> 物料 {material_code}")
        
        db.commit()
        
        print(f"\n迁移完成！")
        print(f"  创建映射: {created_count} 个")
        print(f"  跳过记录: {skipped_count} 个")
        
    except Exception as e:
        db.rollback()
        print(f"\n迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_mappings()

