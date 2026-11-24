"""LLM 调用层：OpenAI 兼容客户端 + 出域 payload 构造。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §7.4 / §12、评审 I5：
- ``AI_LLM_ALLOW_EXTERNAL_DATA=false``（默认）时，叙述 payload 只允许聚合统计，
  不得包含记录键、客户标识、客户名与任何金额列；
- 客户端只依赖标准库 ``urllib``，不引入厂商 SDK；换 Ollama / vLLM / 网关只改配置；
- 所有失败（网络、超时、非 2xx、不可解析）都抛 ``LLMError``，由调用方降级，
  不阻断受控查询主链路。
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol

from backend.services.ai.config import get_settings
from backend.services.ai.intent import QueryResult

# 出域黑名单：记录键、客户标识、客户名、金额列
SENSITIVE_COLUMNS = frozenset({
    "customer_id", "customer_name", "credit_limit", "ar_balance",
    "open_order_amount", "credit_usage_ratio", "amount", "received_amount",
    "outstanding", "unit_price", "total_amount", "order_number",
    "invoice_number", "ncr_number", "result_number", "material_code",
})

_SYSTEM_PROMPT = (
    "你是 DIERP 的受控查询助手。只返回调用方要求的 JSON 或纯文本，"
    "不要编造数字，不要输出任何凭据或额外解释。"
)


class LLMError(RuntimeError):
    """LLM 调用失败（网络/超时/非 2xx/响应不可解析）。"""


class LLMHTTPError(LLMError):
    """非 2xx 响应：保留状态码与错误体（截断），供 429/404/400 分支判定。"""

    def __init__(self, message: str, *, status: int, detail: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail


class LLMResponseError(LLMError):
    """2xx 但响应体不符合 OpenAI 兼容结构（缺 choices / 内容为空等）。"""


class LLMClient(Protocol):
    """最小 LLM 客户端协议：输入 JSON payload，返回字符串。"""

    def complete(
        self, payload: dict[str, Any], *, response_format: str | None = None
    ) -> str: ...


# 网关的“路由别名”不是具体模型，契约稳定性差，不进入自动备选
_NON_DIRECT_MODELS = frozenset({"auto", "fusion"})


def _normalize_base_url(base_url: str) -> str:
    """接受 ``http://host`` 或 ``http://host/v1``，统一为以 ``/v1`` 结尾。"""
    url = (base_url or "").strip().rstrip("/")
    if not url:
        raise LLMError("LLM base_url 为空")
    lower = url.lower()
    if not (lower.endswith("/v1") or "/v1/" in lower):
        url = f"{url}/v1"
    return url


class OpenAICompatibleClient:
    """最小 OpenAI 兼容客户端：``/v1/chat/completions`` 与 ``/v1/models``。

    配置全部来自 ``AISettings``；密钥只写入请求头，不进入异常信息或日志。
    - 每次 ``complete`` 最多 2 次 HTTP 尝试（首次 + 1 次重试），与 LLMProposer 对齐；
    - 429 / 上游模型失效（404）时短暂退避后切换到备选模型（若启用自动发现）；
    - 记录 ``last_model``，供调用方如实标注本次实际使用的模型。
    """

    MAX_ATTEMPTS = 2  # 首次 + 最多 1 次重试
    MAX_FALLBACK_MODELS = 3  # 自动发现的备选数量上限

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 20.0,
        *,
        max_attempts: int | None = None,
        fallback_models: list[str] | None = None,
        discover_fallbacks: bool = False,
        backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        self.model = (model or "").strip()
        if not self.model:
            raise LLMError("LLM model 为空")
        self._api_key = api_key or ""
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts or self.MAX_ATTEMPTS)
        self.backoff_seconds = max(0.0, backoff_seconds)
        self._sleep = sleep or time.sleep
        self._fallback_models = list(fallback_models or [])
        self._discover_fallbacks = discover_fallbacks
        self._last_model: str | None = None
        self._last_attempt_model: str | None = None

    @property
    def last_model(self) -> str:
        """最近一次成功调用实际使用的模型；未调用过时回落到配置模型。"""
        return self._last_model or self.model

    @property
    def last_attempt_model(self) -> str:
        """最近一次 HTTP 尝试（无论成败）使用的模型，用于诊断 429/降级。"""
        return self._last_attempt_model or self.model

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _backoff(self) -> None:
        if self.backoff_seconds > 0:
            self._sleep(self.backoff_seconds)

    def _request_once(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """单次 HTTP 调用；非 2xx 转 ``LLMHTTPError``，响应体异常转 ``LLMResponseError``。"""
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(),
            method="POST" if data else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001
                detail = ""
            raise LLMHTTPError(
                f"LLM HTTP {exc.code}: {detail}", status=exc.code, detail=detail
            ) from None
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            raise LLMError(f"LLM 连接失败: {type(exc).__name__}") from None

        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LLMResponseError(f"LLM 响应不可解析: {type(exc).__name__}") from None
        if not isinstance(parsed, dict):
            raise LLMResponseError("LLM 响应不是 JSON 对象")
        return parsed

    def _request_with_retries(
        self, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET 类只读请求：最多 2 次，5xx/429 退避后重试，4xx 直接失败。"""
        last_error: LLMError | None = None
        for attempt in range(self.max_attempts):
            try:
                return self._request_once(path, payload)
            except LLMHTTPError as exc:
                last_error = exc
                if 400 <= exc.status < 500 and exc.status != 429:
                    raise
                if attempt + 1 < self.max_attempts:
                    self._backoff()
            except LLMError as exc:
                last_error = exc
                if attempt + 1 < self.max_attempts:
                    self._backoff()
        raise last_error or LLMError("LLM 调用失败")

    def _candidate_models(self) -> list[str]:
        if self._discover_fallbacks and not self._fallback_models:
            self._fallback_models = self._discover_fallback_models()
        return [self.model, *self._fallback_models]

    def _discover_fallback_models(self) -> list[str]:
        """从 ``/v1/models`` 里挑可用备选：同族模型优先，排除路由别名。"""
        try:
            data = self._request_with_retries("/models")
        except LLMError:
            return []
        items = data.get("data")
        if not isinstance(items, list):
            return []

        candidates: list[str] = []
        for item in items:
            if not isinstance(item, dict) or item.get("available") is False:
                continue
            model_id = item.get("id")
            if not isinstance(model_id, str) or not model_id:
                continue
            if model_id == self.model or model_id in _NON_DIRECT_MODELS:
                continue
            if model_id.startswith("claude-"):  # Opus/Sonnet/Haiku 槽位同样是自动路由
                continue
            candidates.append(model_id)

        family = self.model.split("-")[0]
        same_family = [mid for mid in candidates if mid.split("-")[0] == family]
        others = [mid for mid in candidates if mid.split("-")[0] != family]
        # 跨族优先作为第一备选：同族模型通常共用同一上游密钥与配额，429 往往一起命中
        ordered = others[:1] + same_family[:2] + others[1:]
        return ordered[: self.MAX_FALLBACK_MODELS]

    def list_models(self) -> list[str]:
        """``GET /v1/models``：返回可用模型 id（只读探测）。"""
        data = self._request_with_retries("/models")
        items = data.get("data")
        if not isinstance(items, list):
            return []
        return [
            str(item.get("id"))
            for item in items
            if isinstance(item, dict) and item.get("id")
        ]

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseError("LLM 响应缺少 choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("LLM 返回内容为空")
        return content.strip()

    def complete(
        self, payload: dict[str, Any], *, response_format: str | None = None
    ) -> str:
        """把结构化 payload 包成一条 user 消息，返回 assistant 文本。

        ``response_format="json_object"`` 会写入 OpenAI 兼容请求体；若上游不认识该字段
        （400 且错误体提到 response_format），第二次尝试自动去掉它，仍保持 ≤2 次调用。
        """
        body: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0,
            "stream": False,
        }

        last_error: LLMError | None = None
        attempts = 0
        for model in self._candidate_models():
            if attempts >= self.max_attempts:
                break
            body["model"] = model
            format_sent = response_format
            while attempts < self.max_attempts:
                attempts += 1
                call_body = dict(body)
                if format_sent:
                    call_body["response_format"] = {"type": format_sent}
                else:
                    call_body.pop("response_format", None)
                try:
                    self._last_attempt_model = model
                    data = self._request_once("/chat/completions", call_body)
                    content = self._extract_content(data)
                    self._last_model = model
                    return content
                except LLMHTTPError as exc:
                    last_error = exc
                    if exc.status == 429:
                        # 上游限流：短暂退避后切换到备选模型（若没有备选则直接失败）
                        self._backoff()
                        break
                    if exc.status == 404:
                        break
                    if (
                        format_sent
                        and exc.status == 400
                        and "response_format" in exc.detail.lower()
                    ):
                        format_sent = None
                        continue
                    if 500 <= exc.status < 600 and attempts < self.max_attempts:
                        self._backoff()
                        continue
                    raise
                except LLMError as exc:
                    last_error = exc
                    if attempts < self.max_attempts:
                        self._backoff()
                        continue
                    raise
        raise last_error or LLMError("LLM 调用失败")


def build_narration_payload(
    result: QueryResult,
    columns: list[str],
    *,
    allow_external_data: bool,
) -> dict[str, Any]:
    """构造叙述层 payload；默认只含聚合统计，不含行级明细。"""
    if allow_external_data:
        return {
            "columns": columns,
            "rows": [{key: row.get(key) for key in columns} for row in result.rows],
        }

    aggregate: dict[str, dict[str, float]] = {}
    for column in columns:
        if column in SENSITIVE_COLUMNS:
            continue
        values = [
            float(row[column])
            for row in result.rows
            if isinstance(row.get(column), (int, float)) and not isinstance(row.get(column), bool)
        ]
        if values:
            aggregate[column] = {
                "count": len(values),
                "sum": round(sum(values), 4),
                "min": min(values),
                "max": max(values),
            }
    return {
        "row_count": len(result.rows),
        "aggregate": aggregate,
    }


def call_narration(client: LLMClient, payload: dict[str, Any]) -> str:
    text = client.complete({"task": "narration", **payload})
    if not isinstance(text, str) or not text.strip():
        raise ValueError("LLM 叙述返回为空")
    return text.strip()


def get_llm_client() -> LLMClient | None:
    """按 ``AISettings`` 构造客户端；未启用或配置不全时返回 None（确定性模板）。

    任何构造失败（空 base_url / 空 model）都降级为 None，不影响问答主链路。
    """
    settings = get_settings()
    if not settings.ai_llm_enabled:
        return None
    try:
        return OpenAICompatibleClient(
            base_url=settings.ai_llm_base_url,
            model=settings.ai_llm_model,
            api_key=settings.ai_llm_api_key,
            timeout=float(settings.ai_llm_timeout_seconds),
            discover_fallbacks=True,
        )
    except LLMError:
        return None
