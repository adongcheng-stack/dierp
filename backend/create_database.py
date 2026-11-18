"""
自动创建数据库脚本
"""
import psycopg2
from psycopg2 import sql
import sys
import os
from dotenv import load_dotenv
import urllib.parse

# 设置UTF-8编码（Windows控制台）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
load_dotenv()

def create_database():
    """创建数据库"""
    # 从环境变量获取数据库连接信息
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hserp_mvp")
    
    # 解析连接字符串
    # 格式: postgresql://user:password@host:port/database
    try:
        # 解析URL
        try:
            parsed = urllib.parse.urlparse(db_url)
            user = parsed.username or "postgres"
            password = parsed.password or "123456"
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
        except Exception as e:
            # 如果解析失败，使用默认值
            print(f"[WARNING] 解析连接字符串失败，使用默认值: {e}")
            user = "postgres"
            password = "postgres"
            host = "localhost"
            port = 5432
        
        print("正在连接到PostgreSQL服务器...")
        print(f"主机: {host}, 端口: {port}, 用户: {user}")
        
        # 连接到PostgreSQL服务器（使用postgres数据库）
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # 连接到postgres数据库以创建新数据库
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
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        print("\n请检查：")
        print("1. PostgreSQL服务是否正在运行")
        print("2. 数据库连接信息是否正确（检查 .env 文件）")
        print("3. 用户名和密码是否正确")
        return False
    except Exception as e:
        print(f"[ERROR] 创建数据库时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("航盛电路ERP系统 - 数据库创建工具")
    print("=" * 50)
    print()
    
    success = create_database()
    
    if success:
        print()
        print("=" * 50)
        print("下一步：运行 'python init_db.py' 初始化数据库表")
        print("=" * 50)
        sys.exit(0)
    else:
        print()
        print("=" * 50)
        print("数据库创建失败，请检查错误信息并重试")
        print("=" * 50)
        sys.exit(1)

