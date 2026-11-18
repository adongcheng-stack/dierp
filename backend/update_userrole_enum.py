"""
更新 userrole 枚举类型，添加新的角色值
"""
import os
import sys
from pathlib import Path

# 设置UTF-8编码（Windows控制台）
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# 添加项目根目录到Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from backend.common.database.base import engine
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(script_dir / '.env')

def update_userrole_enum():
    """更新 userrole 枚举类型"""
    print("=" * 50)
    print("更新 userrole 枚举类型")
    print("=" * 50)
    print()
    
    # 需要添加的新角色值
    new_roles = ['SALES_MANAGER', 'GENERAL_MANAGER']
    
    try:
        with engine.connect() as conn:
            # 检查当前枚举值
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'userrole'
                )
                ORDER BY enumsortorder;
            """))
            existing_values = [row[0] for row in result]
            print(f"当前枚举值: {', '.join(existing_values)}")
            print()
            
            # 添加缺失的枚举值
            for role in new_roles:
                if role not in existing_values:
                    try:
                        print(f"正在添加枚举值: {role}...")
                        # 使用 IF NOT EXISTS 语法（PostgreSQL 9.5+）
                        # 如果版本较低，可能需要先检查是否存在
                        conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{role}'"))
                        conn.commit()
                        print(f"[OK] 成功添加: {role}")
                    except Exception as e:
                        # 如果 IF NOT EXISTS 不支持，尝试直接添加（可能会失败如果已存在）
                        error_msg = str(e)
                        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                            print(f"[SKIP] {role} 已存在，跳过")
                        else:
                            # 尝试不使用 IF NOT EXISTS（适用于较旧版本）
                            try:
                                conn.execute(text(f"ALTER TYPE userrole ADD VALUE '{role}'"))
                                conn.commit()
                                print(f"[OK] 成功添加: {role}")
                            except Exception as e2:
                                print(f"[WARNING] 添加 {role} 失败: {e2}")
                                print("  这可能是因为该值已存在，或者需要重新创建枚举类型")
                else:
                    print(f"[SKIP] {role} 已存在，跳过")
            
            print()
            # 再次检查枚举值
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = 'userrole'
                )
                ORDER BY enumsortorder;
            """))
            final_values = [row[0] for row in result]
            print(f"更新后的枚举值: {', '.join(final_values)}")
            print()
            
        print("=" * 50)
        print("枚举类型更新完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 更新枚举类型失败: {e}")
        print()
        print("如果遇到错误，可以尝试以下SQL命令手动更新：")
        print()
        for role in new_roles:
            print(f"  ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{role}';")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    update_userrole_enum()

