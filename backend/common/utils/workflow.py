"""
轻量级流程引擎 - 支持审核流程和状态流转
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.common.database.base import Base


class WorkflowStatus(str, Enum):
    """流程状态"""
    DRAFT = "DRAFT"  # 草稿
    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 已审核
    REJECTED = "REJECTED"  # 已拒绝
    CANCELLED = "CANCELLED"  # 已取消
    COMPLETED = "COMPLETED"  # 已完成


class WorkflowNode(Base):
    """流程节点"""
    __tablename__ = "workflow_nodes"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(50), ForeignKey("workflows.workflow_id"), nullable=False)  # 添加外键
    node_id = Column(String(50), unique=True, nullable=False, index=True)  # 添加唯一约束
    node_name = Column(String(100), nullable=False)
    node_type = Column(String(50), nullable=False)  # START, APPROVAL, END
    approver_role = Column(String(50))  # 审核人角色
    order = Column(Integer, nullable=False)  # 节点顺序
    config = Column(JSON)  # 节点配置
    
    # 关联
    workflow = relationship("Workflow", back_populates="nodes")
    instances = relationship("WorkflowInstanceNode", back_populates="node")


class Workflow(Base):
    """流程定义"""
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(50), unique=True, nullable=False)
    workflow_name = Column(String(100), nullable=False)
    description = Column(String(500))
    module = Column(String(50))  # SD, ENG, PP, MM
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    nodes = relationship("WorkflowNode", back_populates="workflow", order_by="WorkflowNode.order")
    instances = relationship("WorkflowInstance", back_populates="workflow")


class WorkflowInstance(Base):
    """流程实例"""
    __tablename__ = "workflow_instances"
    
    id = Column(Integer, primary_key=True)
    instance_id = Column(String(50), unique=True, nullable=False)
    workflow_id = Column(String(50), ForeignKey("workflows.workflow_id"), nullable=False)
    business_id = Column(String(50), nullable=False)  # 业务单据ID
    business_type = Column(String(50), nullable=False)  # 业务类型
    status = Column(String(50), default=WorkflowStatus.DRAFT)
    current_node_id = Column(String(50))
    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 关联
    workflow = relationship("Workflow", back_populates="instances")
    node_instances = relationship("WorkflowInstanceNode", back_populates="instance")


class WorkflowInstanceNode(Base):
    """流程实例节点"""
    __tablename__ = "workflow_instance_nodes"
    
    id = Column(Integer, primary_key=True)
    instance_id = Column(String(50), ForeignKey("workflow_instances.instance_id"), nullable=False)
    node_id = Column(String(50), ForeignKey("workflow_nodes.node_id"), nullable=False)  # 现在workflow_nodes.node_id有唯一约束了
    status = Column(String(50), default=WorkflowStatus.PENDING)  # PENDING, APPROVED, REJECTED
    approver = Column(String(50))
    approved_at = Column(DateTime)
    comment = Column(String(500))
    order = Column(Integer, nullable=False)
    
    # 关联
    instance = relationship("WorkflowInstance", back_populates="node_instances")
    node = relationship("WorkflowNode", back_populates="instances")


class WorkflowEngine:
    """流程引擎"""
    
    def __init__(self, db):
        self.db = db
    
    def create_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        nodes: List[Dict],
        module: str = None,
        description: str = None
    ) -> Workflow:
        """创建流程定义"""
        workflow = Workflow(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            description=description,
            module=module
        )
        self.db.add(workflow)
        
        for idx, node_data in enumerate(nodes):
            node = WorkflowNode(
                workflow_id=workflow_id,
                node_id=node_data['node_id'],
                node_name=node_data['node_name'],
                node_type=node_data['node_type'],
                approver_role=node_data.get('approver_role'),
                order=idx + 1,
                config=node_data.get('config', {})
            )
            self.db.add(node)
        
        self.db.commit()
        return workflow
    
    def start_workflow(
        self,
        workflow_id: str,
        business_id: str,
        business_type: str,
        created_by: str
    ) -> WorkflowInstance:
        """启动流程实例"""
        workflow = self.db.query(Workflow).filter(
            Workflow.workflow_id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"流程定义不存在: {workflow_id}")
        
        # 创建流程实例
        instance_id = f"{workflow_id}-{business_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        instance = WorkflowInstance(
            instance_id=instance_id,
            workflow_id=workflow_id,
            business_id=business_id,
            business_type=business_type,
            status=WorkflowStatus.PENDING,
            created_by=created_by
        )
        self.db.add(instance)
        
        # 为所有节点创建实例（这样前端可以显示完整的评审流程）
        nodes = sorted(workflow.nodes, key=lambda x: x.order)
        first_node = nodes[0] if nodes else None
        
        if first_node:
            instance.current_node_id = first_node.node_id
            
            # 为所有节点创建实例（这样前端可以显示完整的评审流程）
            for node in nodes:
                # 所有节点初始状态都是 PENDING，前端会根据 current_node 来判断哪个是当前节点
                node_instance = WorkflowInstanceNode(
                    instance_id=instance_id,
                    node_id=node.node_id,
                    status=WorkflowStatus.PENDING,
                    order=node.order
                )
                self.db.add(node_instance)
        
        self.db.commit()
        return instance
    
    def approve(
        self,
        instance_id: str,
        approver: str,
        comment: str = None
    ) -> WorkflowInstance:
        """审核通过"""
        instance = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.instance_id == instance_id
        ).first()
        
        if not instance:
            raise ValueError(f"流程实例不存在: {instance_id}")
        
        # 更新当前节点状态
        current_node_instance = self.db.query(WorkflowInstanceNode).filter(
            WorkflowInstanceNode.instance_id == instance_id,
            WorkflowInstanceNode.node_id == instance.current_node_id
        ).first()
        
        if current_node_instance:
            current_node_instance.status = WorkflowStatus.APPROVED
            current_node_instance.approver = approver
            current_node_instance.approved_at = datetime.utcnow()
            current_node_instance.comment = comment
        
        # 移动到下一个节点
        workflow = instance.workflow
        nodes = sorted(workflow.nodes, key=lambda x: x.order)
        current_node = next((n for n in nodes if n.node_id == instance.current_node_id), None)
        
        if current_node:
            current_index = nodes.index(current_node)
            if current_index < len(nodes) - 1:
                next_node = nodes[current_index + 1]
                instance.current_node_id = next_node.node_id
                
                # 创建下一个节点实例
                next_node_instance = WorkflowInstanceNode(
                    instance_id=instance_id,
                    node_id=next_node.node_id,
                    status=WorkflowStatus.PENDING,
                    order=next_node.order
                )
                self.db.add(next_node_instance)
            else:
                # 流程完成
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.utcnow()
        
        self.db.commit()
        return instance
    
    def reject(
        self,
        instance_id: str,
        approver: str,
        comment: str
    ) -> WorkflowInstance:
        """审核拒绝"""
        instance = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.instance_id == instance_id
        ).first()
        
        if not instance:
            raise ValueError(f"流程实例不存在: {instance_id}")
        
        # 更新当前节点状态
        current_node_instance = self.db.query(WorkflowInstanceNode).filter(
            WorkflowInstanceNode.instance_id == instance_id,
            WorkflowInstanceNode.node_id == instance.current_node_id
        ).first()
        
        if current_node_instance:
            current_node_instance.status = WorkflowStatus.REJECTED
            current_node_instance.approver = approver
            current_node_instance.approved_at = datetime.utcnow()
            current_node_instance.comment = comment
        
        # 流程结束
        instance.status = WorkflowStatus.REJECTED
        instance.completed_at = datetime.utcnow()
        
        self.db.commit()
        return instance
    
    def get_instance_status(self, instance_id: str) -> Dict:
        """获取流程实例状态"""
        try:
            instance = self.db.query(WorkflowInstance).filter(
                WorkflowInstance.instance_id == instance_id
            ).first()
            
            if not instance:
                return None
            
            # 使用 join 加载节点信息，避免 N+1 查询
            from sqlalchemy.orm import joinedload
            node_instances = self.db.query(WorkflowInstanceNode).filter(
                WorkflowInstanceNode.instance_id == instance_id
            ).options(joinedload(WorkflowInstanceNode.node)).order_by(WorkflowInstanceNode.order).all()
            
            # 使用字典去重，确保每个 node_id 只出现一次（保留最新的状态）
            nodes_dict = {}
            for ni in node_instances:
                # 安全地获取节点名称
                node_name = ''
                if ni.node:
                    node_name = ni.node.node_name
                else:
                    # 如果节点关系未加载，尝试从数据库查询
                    node = self.db.query(WorkflowNode).filter(
                        WorkflowNode.node_id == ni.node_id
                    ).first()
                    if node:
                        node_name = node.node_name
                
                # 安全地处理日期时间
                approved_at_str = None
                if ni.approved_at:
                    if isinstance(ni.approved_at, datetime):
                        approved_at_str = ni.approved_at.isoformat()
                    else:
                        approved_at_str = str(ni.approved_at)
                
                node_data = {
                    'node_id': ni.node_id,
                    'node_name': node_name,
                    'status': ni.status,
                    'approver': ni.approver,
                    'approved_at': approved_at_str,
                    'comment': ni.comment,
                    'order': ni.order
                }
                
                # 如果节点已存在，保留状态更优先的（APPROVED > REJECTED > PENDING）
                if ni.node_id in nodes_dict:
                    existing = nodes_dict[ni.node_id]
                    status_priority = {'APPROVED': 3, 'REJECTED': 2, 'PENDING': 1}
                    if status_priority.get(ni.status, 0) > status_priority.get(existing['status'], 0):
                        nodes_dict[ni.node_id] = node_data
                else:
                    nodes_dict[ni.node_id] = node_data
            
            # 转换为列表并按 order 排序
            nodes_data = sorted(nodes_dict.values(), key=lambda x: x.get('order', 0))
            
            return {
                'instance_id': instance.instance_id,
                'status': instance.status,
                'current_node': instance.current_node_id,
                'nodes': nodes_data
            }
        except Exception as e:
            print(f"获取流程实例状态错误: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise

