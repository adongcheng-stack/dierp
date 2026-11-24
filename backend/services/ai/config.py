"""AI 语义底座配置（19 个环境变量，唯一读取入口）。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §12。
所有配置只在这里读取；其它模块通过 ``get_settings()`` 获得同一份不可变实例。
"""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class AISettings(BaseSettings):
    """AI 运行时配置（字段名与 AI_* 环境变量一一对应，大小写不敏感）。"""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # 总开关 / ChatBI 开关（评审 S6：可独立关闭）
    ai_enabled: bool = True
    ai_chatbi_enabled: bool = True

    # LLM（默认关闭，使用确定性解析器）
    ai_llm_enabled: bool = False
    ai_llm_base_url: str = ""
    ai_llm_api_key: str = ""
    ai_llm_model: str = ""
    ai_llm_timeout_seconds: int = 20
    ai_llm_narration_enabled: bool = False
    ai_llm_allow_external_data: bool = False

    # 查询与限流
    ai_max_rows: int = 200
    ai_max_question_chars: int = 500
    ai_rate_limit_per_minute: int = 20
    ai_query_timeout_seconds: int = 5

    # 本体检索
    ai_sparql_enabled: bool = False
    ai_ontology_cache_ttl_seconds: int = 300

    # 日志与审计
    ai_log_prompts: bool = False
    ai_log_question: bool = True

    # MCP 只读工具层（token 为空时 fail-closed，不开放）
    ai_mcp_token: str = ""
    ai_mcp_role: str = "GENERAL_MANAGER"

    # MES 跨库只读查询（默认关闭；凭据只从环境变量注入，禁止落盘）
    mes_query_enabled: bool = False
    mes_db_host: str = "127.0.0.1"
    mes_db_port: int = 3306
    mes_db_name: str = "mesdb"
    mes_db_user: str = ""
    mes_db_password: SecretStr = SecretStr("")
    mes_query_timeout_seconds: int = 5
    mes_query_max_rows: int = 200

    @property
    def enabled(self) -> bool:
        return self.ai_enabled

    @property
    def mes_ready(self) -> bool:
        """MES 查询是否具备可执行条件：开关打开且账号/密码已注入。"""
        return bool(
            self.mes_query_enabled
            and self.mes_db_user
            and self.mes_db_password.get_secret_value()
        )

    @model_validator(mode="after")
    def _validate_llm_consistency(self) -> "AISettings":
        """启动一致性校验：配置矛盾时拒绝启动，而不是运行时静默降级。"""
        if not self.ai_llm_enabled:
            return self

        if not self.ai_llm_base_url or not self.ai_llm_model:
            raise ValueError(
                "AI_LLM_ENABLED=true 时必须同时配置 AI_LLM_BASE_URL 与 AI_LLM_MODEL"
            )

        parsed = urlparse(self.ai_llm_base_url)
        host = (parsed.hostname or "").lower()
        is_local = host in _LOCAL_HOSTS
        if not is_local and parsed.scheme != "https":
            raise ValueError(
                "AI_LLM_BASE_URL 指向非本机地址时必须使用 https://（本地模型可用 http://localhost）"
            )
        if not is_local and not self.ai_llm_allow_external_data:
            raise ValueError(
                "AI_LLM_BASE_URL 指向公网端点但 AI_LLM_ALLOW_EXTERNAL_DATA=false："
                "拒绝启动，避免把行级数据发送到外部 LLM"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> AISettings:
    """读取并缓存配置；测试用 ``get_settings.cache_clear()`` + monkeypatch 覆盖。"""
    return AISettings()
