"""
简单的数据库创建脚本（交互式）
"""
import psycopg2
from psycopg2 import sql
import sys

# 设置UTF-8编码（Windows控制台）
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

def create_database():
    """创建数据库"""
    print("=" * 50)
    print("航盛电路ERP系统 - 数据库创建工具")
    print("=" * 50)
    print()
    
    # 获取连接信息
    print("请输入PostgreSQL连接信息（直接回车使用默认值）：")
    host = input("主机 [localhost]: ").strip() or "localhost"
    port = input("端口 [5432]: ").strip() or "5432"
    user = input("用户名 [postgres]: ").strip() or "postgres"
    password = input("密码: ").strip()
    
    if not password:
        print("[ERROR] 密码不能为空！")
        return False
    
    try:
        print()
        print("正在连接到PostgreSQL服务器...")
        
        # 连接到PostgreSQL服务器（使用postgres数据库）
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 检查数据库是否已存在
        cursor.execute("""
            SELECT 1 FROM pg_database WHERE datname = 'hserp_mvp'
        """)
        
        exists = cursor.fetchone()
        
        if exists:
            print("[OK] 数据库 'hserp_mvp' 已存在，跳过创建。")
        else:
            # 创建数据库
            print("正在创建数据库 'hserp_mvp'...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier('hserp_mvp')
            ))
            print("[OK] 数据库 'hserp_mvp' 创建成功！")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 50)
        print("下一步：运行 'py init_db.py' 初始化数据库表")
        print("=" * 50)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        print()
        print("请检查：")
        print("1. PostgreSQL服务是否正在运行")
        print("2. 用户名和密码是否正确")
        print("3. 主机和端口是否正确")
        return False
    except Exception as e:
        print(f"[ERROR] 创建数据库时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_database()
    sys.exit(0 if success else 1)

