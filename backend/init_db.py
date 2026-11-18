"""
数据库初始化脚本
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
# 这样无论从哪个目录运行脚本都能找到backend模块
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from backend.common.database.base import Base, engine
from backend.common.models import (
    user, sd, mm, eng, pp, planning
)
from backend.common.utils.workflow import (
    Workflow, WorkflowNode, WorkflowInstance, WorkflowInstanceNode, WorkflowEngine
)
from backend.common.models.user import User, UserRole
from backend.api.routers.auth import get_password_hash

def init_database():
    """初始化数据库"""
    print("=" * 50)
    print("航盛电路ERP系统 - 数据库初始化")
    print("=" * 50)
    print()
    
    try:
        print("正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        print("[OK] 数据库表创建完成！")
        print()
    
        # 创建默认管理员用户
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # 检查是否已存在管理员用户
            admin = db.query(User).filter(User.username == "admin").first()
            if not admin:
                admin = User(
                    username="admin",
                    email="admin@hserp.com",
                    password_hash=get_password_hash("admin123"),
                    full_name="系统管理员",
                    role=UserRole.ADMIN,
                    department="IT",
                    is_active=True
                )
                db.add(admin)
                db.commit()
                print("[OK] 默认管理员用户创建成功！")
                print("  用户名: admin")
                print("  密码: admin123")
                print()
            else:
                print("[OK] 管理员用户已存在")
                print()
            
            # 创建订单评审工作流定义
            workflow_engine = WorkflowEngine(db)
            existing_workflow = db.query(Workflow).filter(
                Workflow.workflow_id == "SALES_ORDER_REVIEW"
            ).first()
            
            if not existing_workflow:
                workflow_engine.create_workflow(
                    workflow_id="SALES_ORDER_REVIEW",
                    workflow_name="销售订单多部门评审流程",
                    description="销售订单需要经过销售、工程、物料、财务四个部门顺序评审",
                    module="SD",
                    nodes=[
                        {
                            "node_id": "SALES_REVIEW",
                            "node_name": "销售部门评审",
                            "node_type": "APPROVAL",
                            "approver_role": "SALES_MANAGER",
                            "config": {"required": True}
                        },
                        {
                            "node_id": "ENGINEERING_REVIEW",
                            "node_name": "工程部门评审",
                            "node_type": "APPROVAL",
                            "approver_role": "ENGINEER",
                            "config": {"required": True}
                        },
                        {
                            "node_id": "MATERIAL_REVIEW",
                            "node_name": "物料部门评审",
                            "node_type": "APPROVAL",
                            "approver_role": "WAREHOUSE",
                            "config": {"required": True}
                        },
                        {
                            "node_id": "FINANCE_REVIEW",
                            "node_name": "财务部门评审",
                            "node_type": "APPROVAL",
                            "approver_role": "FINANCE",
                            "config": {"required": True}
                        }
                    ]
                )
                print("[OK] 订单评审工作流定义创建成功！")
                print()
            else:
                print("[OK] 订单评审工作流定义已存在")
                print()
        except Exception as e:
            print(f"[ERROR] 初始化数据失败: {e}")
            db.rollback()
            raise
        finally:
            db.close()
        
        print("=" * 50)
        print("数据库初始化完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 数据库初始化失败: {e}")
        print()
        print("请检查：")
        print("1. PostgreSQL服务是否正在运行")
        print("2. 数据库 'hserp_mvp' 是否已创建")
        print("3. .env 文件中的数据库连接信息是否正确")
        print("   格式: DATABASE_URL=postgresql://postgres:密码@localhost:5432/hserp_mvp")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_database()

