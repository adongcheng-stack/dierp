"""AI 问答审计模型（语义级；HTTP 级轨迹仍在 operation_logs）。"""
from sqlalchemy import Column, Integer, JSON, String, Text

from backend.common.models.base import BaseModel


class AiQueryLog(BaseModel):
    """一次 AI 查询的结构化审计记录（设计 §9.1）。"""

    __tablename__ = "ai_query_logs"

    trace_id = Column(String(36), unique=True, nullable=False, index=True, comment="本次问答链路 ID")
    request_id = Column(String(36), index=True, comment="关联 operation_logs.request_id")
    username = Column(String(50), index=True)
    role = Column(String(30))
    question = Column(Text, nullable=True, comment="AI_LOG_QUESTION=false 时为 NULL")
    question_sha256 = Column(String(64), comment="关闭原文时用于去重与趋势")
    intent_code = Column(String(50), index=True)
    intent_json = Column(JSON)
    status = Column(String(30), nullable=False, index=True, comment="OK / REJECTED_* / FAILED")
    error_code = Column(String(50), comment="与设计 §7.5 的错误码一一对应")
    shacl_status = Column(String(20), comment="passed / partial / skipped / failed")
    reject_reason = Column(String(300))
    model = Column(String(80))
    latency_ms = Column(Integer)
    row_count = Column(Integer, default=0)
    provenance_json = Column(JSON, comment="只存表名/单号/IRI，不存整行数据")
    feedback_score = Column(Integer, comment="-1 / 0 / 1")
    feedback_comment = Column(Text)
