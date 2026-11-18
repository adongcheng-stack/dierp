"""
检查数据库表是否存在
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import inspect
from backend.common.database.base import engine

def check_tables():
    """检查数据库表"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("=" * 50)
    print("数据库表检查")
    print("=" * 50)
    print(f"\n已创建的表 ({len(tables)} 个):")
    for table in sorted(tables):
        print(f"  - {table}")
    
    print(f"\n关键表检查:")
    key_tables = [
        'material_transactions',
        'material_issues',
        'materials',
        'production_orders'
    ]
    
    for table in key_tables:
        exists = table in tables
        status = "[存在]" if exists else "[不存在]"
        print(f"  {status}: {table}")
    
    if 'material_transactions' not in tables:
        print("\n⚠️  警告: material_transactions 表不存在！")
        print("请运行以下命令创建表:")
        print("  cd backend")
        print("  python init_db.py")

if __name__ == "__main__":
    try:
        check_tables()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

