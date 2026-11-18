"""
快速创建工作流定义的脚本
用于修复缺失的工作流定义
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

from sqlalchemy.orm import sessionmaker
from backend.common.database.base import engine
from backend.common.utils.workflow import Workflow, WorkflowEngine

def create_workflow_definitions():
    """创建工作流定义"""
    print("=" * 50)
    print("创建工作流定义")
    print("=" * 50)
    print()
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        workflow_engine = WorkflowEngine(db)
        
        # 检查并创建 SALES_ORDER_REVIEW 工作流
        existing_workflow = db.query(Workflow).filter(
            Workflow.workflow_id == "SALES_ORDER_REVIEW"
        ).first()
        
        if not existing_workflow:
            print("正在创建 SALES_ORDER_REVIEW 工作流定义...")
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
            print("[OK] SALES_ORDER_REVIEW 工作流定义创建成功！")
        else:
            print("[OK] SALES_ORDER_REVIEW 工作流定义已存在")
        
        print()
        print("=" * 50)
        print("工作流定义创建完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 创建工作流定义失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_workflow_definitions()

