"""
API网关 - 主入口
"""
from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import jwt
from backend.api.routers import sd, eng, pp, mm, auth, users, planning, qms, traceability, dashboard, purchase, finance, admin, system, ai as ai_router
from backend.api.routers.auth import (
    ALGORITHM,
    NEW_TOKEN_HEADER,
    SECRET_KEY,
    maybe_refresh_token,
    require_read_permission,
    require_write_permission,
)
from backend.common.exceptions import BusinessException
from backend.common.models.audit import OperationLog
from backend.common.utils import logger as app_logger
from backend.common.utils.security_policy import WRITE_METHODS
import os
import uuid

app = FastAPI(
    title="DIERP ERP 管理系统 · Demo",
    description="轻量化ERP系统，验证PCB制造行业核心业务流程",
    version="1.0.0"
)

# CORS配置：默认仅放行本地演示端口，可用 ERP_CORS_ORIGINS 环境变量覆盖（逗号分隔）
_cors_origins = os.getenv(
    "ERP_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3100,http://localhost:3200,"
    "http://127.0.0.1:3000,http://127.0.0.1:3100,http://127.0.0.1:3200",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-New-Access-Token"],  # 静默续期：允许前端读取换发的 token
)


def _identity_from_header(auth_header: str) -> tuple[str | None, str | None]:
    """从 JWT 读取用户名/角色（不查库、不校验过期，审计用途）。"""
    if not auth_header.startswith("Bearer "):
        return None, None
    try:
        payload = jwt.decode(
            auth_header[7:], SECRET_KEY, algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
    except Exception:
        return None, None
    role = payload.get("role")
    return payload.get("sub"), str(role) if role is not None else None


# 请求 ID + 静默续期 + 审计日志（写操作）
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    auth_header = request.headers.get("Authorization", "")
    username, role = _identity_from_header(auth_header)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    if auth_header.startswith("Bearer "):
        new_token = maybe_refresh_token(auth_header[7:])
        if new_token:
            response.headers[NEW_TOKEN_HEADER] = new_token

    # 只审计写操作；审计失败绝不阻断业务请求
    if request.method in WRITE_METHODS:
        # 复用 get_db（含测试依赖覆盖），避免审计写到与业务不同的库
        from backend.common.database.base import get_db

        factory = app.dependency_overrides.get(get_db, get_db)
        generator = factory()
        session = next(generator)
        try:
            session.add(
                OperationLog(
                    request_id=request_id,
                    username=username,
                    role=role,
                    method=request.method,
                    path=request.url.path[:500],
                    status_code=response.status_code,
                    client_ip=request.client.host if request.client else None,
                )
            )
            session.commit()
        except Exception as exc:  # pragma: no cover - 审计降级路径
            session.rollback()
            app_logger.log_error("审计日志写入失败", error=exc, path=request.url.path)
        finally:
            try:
                generator.close()
            except (StopIteration, RuntimeError):
                pass

    return response


# 全局异常处理器
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


# 注册路由（写操作统一过 RBAC 域权限门，读操作统一过读权限门；
# auth 为登录入口必须匿名可达，不挂任何门）。
# 权限矩阵来自本体生成物：ontology/src/security.ttl → security_policy.py
_read_gate = [Depends(require_read_permission)]
_gates = [Depends(require_write_permission), Depends(require_read_permission)]
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api", tags=["用户管理"], dependencies=_gates)
app.include_router(sd.router, prefix="/api/sd", tags=["销售与分销"], dependencies=_gates)
app.include_router(eng.router, prefix="/api/eng", tags=["工程管理"], dependencies=_gates)
app.include_router(pp.router, prefix="/api/pp", tags=["生产计划与控制"], dependencies=_gates)
app.include_router(mm.router, prefix="/api/mm", tags=["物料管理"], dependencies=_gates)
app.include_router(planning.router, prefix="/api/planning", tags=["计划与控制"], dependencies=_gates)
app.include_router(qms.router, prefix="/api/qms", tags=["质量管理"], dependencies=_gates)
app.include_router(purchase.router, prefix="/api/purchase", tags=["采购管理"], dependencies=_gates)
app.include_router(finance.router, prefix="/api/finance", tags=["财务管理"], dependencies=_gates)
app.include_router(traceability.router, prefix="/api/traceability", tags=["双向追溯"], dependencies=_read_gate)
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["经营看板"], dependencies=_read_gate)
app.include_router(admin.router, prefix="/api/admin", tags=["管理/审计"], dependencies=_gates)
app.include_router(system.router, prefix="/api/system", tags=["组织架构/系统管理"], dependencies=_gates)
# AI 域：只读、强制登录；不挂 _gates（见 backend/api/routers/ai.py 顶部说明）
app.include_router(ai_router.router, prefix="/api/ai", tags=["AI 助手"],
                   dependencies=[Depends(ai_router.require_ai_access)])


@app.get("/")
async def root():
    return {"message": "DIERP ERP 管理系统 · Demo API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

