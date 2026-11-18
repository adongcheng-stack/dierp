"""
初始化工作流定义
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import sessionmaker
from backend.common.database.base import engine
from backend.common.utils.workflow import WorkflowEngine, Workflow

def init_workflows():
    """初始化工作流定义"""
    print("=" * 50)
    print("工作流定义初始化")
    print("=" * 50)
    print()
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        engine_obj = WorkflowEngine(db)
        
        # 检查报价单审核工作流是否已存在
        existing = db.query(Workflow).filter(
            Workflow.workflow_id == "QUOTATION_APPROVAL"
        ).first()
        
        if existing:
            print("[OK] 报价单审核工作流已存在，跳过创建")
        else:
            # 创建报价单三级审核工作流
            print("正在创建报价单审核工作流...")
            nodes = [
                {
                    "node_id": "SALES_MANAGER_APPROVAL",
                    "node_name": "销售经理审核",
                    "node_type": "APPROVAL",
                    "approver_role": "SALES_MANAGER",
                    "config": {}
                },
                {
                    "node_id": "FINANCE_APPROVAL",
                    "node_name": "财务审核",
                    "node_type": "APPROVAL",
                    "approver_role": "FINANCE",
                    "config": {}
                },
                {
                    "node_id": "GENERAL_MANAGER_APPROVAL",
                    "node_name": "总经理审核",
                    "node_type": "APPROVAL",
                    "approver_role": "GENERAL_MANAGER",
                    "config": {}
                }
            ]
            
            workflow = engine_obj.create_workflow(
                workflow_id="QUOTATION_APPROVAL",
                workflow_name="报价单三级审核流程",
                nodes=nodes,
                module="SD",
                description="报价单三级审核流程：销售经理→财务→总经理"
            )
            print(f"[OK] 报价单审核工作流创建成功: {workflow.workflow_id}")
        
        print()
        print("=" * 50)
        print("工作流定义初始化完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 初始化工作流失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    init_workflows()

