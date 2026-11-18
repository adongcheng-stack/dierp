"""
检查工作流节点定义的脚本
用于排查权限问题
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
from backend.common.utils.workflow import Workflow, WorkflowNode
from backend.common.models.user import User

def check_workflow_nodes():
    """检查工作流节点定义"""
    print("=" * 50)
    print("检查工作流节点定义")
    print("=" * 50)
    print()
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 检查 SALES_ORDER_REVIEW 工作流
        workflow = db.query(Workflow).filter(
            Workflow.workflow_id == "SALES_ORDER_REVIEW"
        ).first()
        
        if not workflow:
            print("[ERROR] SALES_ORDER_REVIEW 工作流定义不存在")
            return
        
        print(f"工作流ID: {workflow.workflow_id}")
        print(f"工作流名称: {workflow.workflow_name}")
        print()
        
        # 检查所有节点
        nodes = db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == "SALES_ORDER_REVIEW"
        ).order_by(WorkflowNode.order).all()
        
        print(f"节点数量: {len(nodes)}")
        print()
        
        for node in nodes:
            print(f"节点ID: {node.node_id}")
            print(f"  节点名称: {node.node_name}")
            print(f"  要求角色(原始): {node.approver_role}")
            print(f"  要求角色(类型): {type(node.approver_role)}")
            print(f"  要求角色(字符串): {str(node.approver_role) if node.approver_role else None}")
            print(f"  要求角色(repr): {repr(node.approver_role)}")
            print()
        
        # 检查用户 xiaojingli
        user = db.query(User).filter(User.username == "xiaojingli").first()
        if user:
            print(f"用户: {user.username}")
            print(f"  角色(原始): {user.role}")
            print(f"  角色(值): {user.role.value}")
            print(f"  角色(类型): {type(user.role.value)}")
            print(f"  角色(字符串): {str(user.role.value)}")
            print(f"  角色(repr): {repr(user.role.value)}")
            print()
            
            # 检查匹配
            if nodes:
                first_node = nodes[0]
                node_role = str(first_node.approver_role) if first_node.approver_role else None
                user_role = str(user.role.value)
                
                print(f"匹配测试:")
                print(f"  节点角色: '{node_role}'")
                print(f"  用户角色: '{user_role}'")
                print(f"  直接比较: {user_role == node_role}")
                print(f"  是否在列表中: {user_role in ['SALES', 'SALES_MANAGER', 'ADMIN']}")
                print(f"  节点角色是否等于SALES_MANAGER: {node_role == 'SALES_MANAGER'}")
                print()
        else:
            print("[ERROR] 用户 xiaojingli 不存在")
        
    except Exception as e:
        print(f"[ERROR] 检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_workflow_nodes()

