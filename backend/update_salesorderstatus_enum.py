"""
更新销售订单状态枚举类型，添加 RECONCILED 和 CLOSED 状态
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def update_salesorderstatus_enum():
    """更新 salesorderstatus 枚举类型，添加 RECONCILED 和 CLOSED 值"""
    # 从环境变量获取数据库连接信息
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "hserp")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    
    try:
        # 连接数据库（使用 client_encoding 避免编码问题）
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            client_encoding='UTF8'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查 RECONCILED 是否已存在
        cursor.execute("""
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'RECONCILED' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'salesorderstatus')
        """)
        
        if cursor.fetchone():
            print("[OK] RECONCILED status already exists, no need to add")
        else:
            # 添加 RECONCILED 到枚举类型
            cursor.execute("ALTER TYPE salesorderstatus ADD VALUE IF NOT EXISTS 'RECONCILED'")
            print("[OK] Successfully added RECONCILED status to salesorderstatus enum type")
        
        # 检查 CLOSED 是否已存在
        cursor.execute("""
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'CLOSED' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'salesorderstatus')
        """)
        
        if cursor.fetchone():
            print("[OK] CLOSED status already exists, no need to add")
        else:
            # 添加 CLOSED 到枚举类型
            cursor.execute("ALTER TYPE salesorderstatus ADD VALUE IF NOT EXISTS 'CLOSED'")
            print("[OK] Successfully added CLOSED status to salesorderstatus enum type")
        
        cursor.close()
        conn.close()
        print("[OK] Database enum type update completed")
        
    except Exception as e:
        print(f"[ERROR] Failed to update enum type: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    update_salesorderstatus_enum()

