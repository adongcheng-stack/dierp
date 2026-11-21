"""审计日志模型：高危写操作的不可变事实记录（本体公理 A19 落地）。

对应安全本体 security.ttl 的 :AuditEntry ⊑ :EventRecord。
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text
from datetime import datetime

from backend.common.database.base import Base


class OperationLog(Base):
    """操作审计日志（append-only：业务代码不得 UPDATE/DELETE）。"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(36), nullable=False, index=True, comment="请求 ID，串联一次 HTTP 调用")
    username = Column(String(50), nullable=True, index=True, comment="操作人；匿名请求为 null")
    role = Column(String(50), nullable=True, comment="操作角色")
    method = Column(String(10), nullable=False, comment="HTTP 方法")
    path = Column(String(500), nullable=False, comment="请求路径（不含查询串）")
    status_code = Column(Integer, nullable=False, comment="响应状态码")
    client_ip = Column(String(64), nullable=True, comment="客户端 IP")
    detail = Column(Text, nullable=True, comment="可选补充信息")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
