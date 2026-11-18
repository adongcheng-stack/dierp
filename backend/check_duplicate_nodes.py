"""
检查工作流节点是否重复的脚本
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
from backend.common.utils.workflow import Workflow, WorkflowNode, WorkflowInstance, WorkflowInstanceNode

def check_duplicate_nodes():
    """检查工作流节点是否重复"""
    print("=" * 50)
    print("检查工作流节点是否重复")
    print("=" * 50)
    print()
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 检查工作流定义中的节点
        print("1. 检查工作流定义中的节点:")
        print("-" * 50)
        nodes = db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == "SALES_ORDER_REVIEW"
        ).order_by(WorkflowNode.order).all()
        
        print(f"节点总数: {len(nodes)}")
        print()
        
        node_names = {}
        for node in nodes:
            node_name = node.node_name
            if node_name not in node_names:
                node_names[node_name] = []
            node_names[node_name].append({
                'node_id': node.node_id,
                'order': node.order,
                'approver_role': node.approver_role
            })
            print(f"  节点 {node.order}: {node.node_id} - {node.node_name} (角色: {node.approver_role})")
        
        print()
        print("2. 检查重复的节点名称:")
        print("-" * 50)
        duplicates = {name: nodes_list for name, nodes_list in node_names.items() if len(nodes_list) > 1}
        if duplicates:
            print(f"发现 {len(duplicates)} 个重复的节点名称:")
            for name, nodes_list in duplicates.items():
                print(f"  '{name}' 出现了 {len(nodes_list)} 次:")
                for n in nodes_list:
                    print(f"    - {n['node_id']} (order: {n['order']}, 角色: {n['approver_role']})")
        else:
            print("未发现重复的节点名称")
        
        print()
        print("3. 检查工作流实例中的节点实例:")
        print("-" * 50)
        # 获取最近的一个工作流实例
        instance = db.query(WorkflowInstance).filter(
            WorkflowInstance.workflow_id == "SALES_ORDER_REVIEW"
        ).order_by(WorkflowInstance.created_at.desc()).first()
        
        if instance:
            print(f"工作流实例: {instance.instance_id}")
            print(f"当前节点: {instance.current_node_id}")
            print()
            
            node_instances = db.query(WorkflowInstanceNode).filter(
                WorkflowInstanceNode.instance_id == instance.instance_id
            ).order_by(WorkflowInstanceNode.order).all()
            
            print(f"节点实例总数: {len(node_instances)}")
            print()
            
            instance_node_names = {}
            for ni in node_instances:
                # 获取节点信息
                node = db.query(WorkflowNode).filter(
                    WorkflowNode.node_id == ni.node_id
                ).first()
                
                if node:
                    node_name = node.node_name
                    if node_name not in instance_node_names:
                        instance_node_names[node_name] = []
                    instance_node_names[node_name].append({
                        'node_id': ni.node_id,
                        'order': ni.order,
                        'status': ni.status
                    })
                    print(f"  节点实例 {ni.order}: {ni.node_id} - {node.node_name} (状态: {ni.status})")
            
            print()
            print("4. 检查实例中重复的节点名称:")
            print("-" * 50)
            instance_duplicates = {name: nodes_list for name, nodes_list in instance_node_names.items() if len(nodes_list) > 1}
            if instance_duplicates:
                print(f"发现 {len(instance_duplicates)} 个重复的节点名称:")
                for name, nodes_list in instance_duplicates.items():
                    print(f"  '{name}' 出现了 {len(nodes_list)} 次:")
                    for n in nodes_list:
                        print(f"    - {n['node_id']} (order: {n['order']}, 状态: {n['status']})")
            else:
                print("未发现重复的节点名称")
        else:
            print("未找到工作流实例")
        
    except Exception as e:
        print(f"[ERROR] 检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_duplicate_nodes()

