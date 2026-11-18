"""
API网关 - 主入口
"""
from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routers import sd, eng, pp, mm, auth, users, planning, qms, traceability, dashboard
from backend.api.routers.auth import require_write_permission
from backend.common.exceptions import BusinessException
import os

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
)

# 全局异常处理器
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


# 注册路由（写操作统一过 RBAC 域权限门；auth 为登录入口必须匿名可达）
_write_gate = [Depends(require_write_permission)]
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api", tags=["用户管理"], dependencies=_write_gate)
app.include_router(sd.router, prefix="/api/sd", tags=["销售与分销"], dependencies=_write_gate)
app.include_router(eng.router, prefix="/api/eng", tags=["工程管理"], dependencies=_write_gate)
app.include_router(pp.router, prefix="/api/pp", tags=["生产计划与控制"], dependencies=_write_gate)
app.include_router(mm.router, prefix="/api/mm", tags=["物料管理"], dependencies=_write_gate)
app.include_router(planning.router, prefix="/api/planning", tags=["计划与控制"], dependencies=_write_gate)
app.include_router(qms.router, prefix="/api/qms", tags=["质量管理"], dependencies=_write_gate)
app.include_router(traceability.router, prefix="/api/traceability", tags=["双向追溯"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["经营看板"])


@app.get("/")
async def root():
    return {"message": "DIERP ERP 管理系统 · Demo API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

