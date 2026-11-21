"""
认证路由

JWT 的签发/校验在这里；"谁能写/读"的策略来自本体生成物 security_policy.py，
由 backend/ontology/generate_security.py 从 ontology/src/security.ttl 生成。
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from backend.common.database.base import get_db
from backend.common.models.user import User, UserRole
from backend.common.models.admin import LoginLog, LoginStatus
from backend.common.utils import logger as app_logger
from backend.common.utils.security_policy import (
    JWT_ALGORITHM as ALGORITHM,
    JWT_INSECURE_PLACEHOLDER,
    JWT_REFRESH_THRESHOLD_MINUTES as TOKEN_REFRESH_THRESHOLD_MINUTES,
    JWT_SECRET_KEY_ENV,
    JWT_TOKEN_EXPIRE_MINUTES as ACCESS_TOKEN_EXPIRE_MINUTES,
    READ_OPEN_DOMAINS,
    READ_ROLE_POLICY,
    WRITE_METHODS,
    WRITE_ROLE_POLICY,
)
import os
import secrets
from pathlib import Path

router = APIRouter()


def _resolve_secret_key() -> str:
    """读取 JWT 密钥；占位默认值时生成随机密钥并落盘，避免公开默认密钥。

    生产环境必须显式设置 SECRET_KEY；演示环境未配置时自动生成一次并复用
    （保存在 backend/.secret_key，已 gitignore），重启后 token 仍然有效。
    """
    configured = os.getenv(JWT_SECRET_KEY_ENV, "").strip()
    if configured and configured != JWT_INSECURE_PLACEHOLDER:
        return configured

    key_file = Path(__file__).resolve().parents[2] / ".secret_key"
    if key_file.exists():
        persisted = key_file.read_text(encoding="utf-8").strip()
        if persisted and persisted != JWT_INSECURE_PLACEHOLDER:
            return persisted

    generated = secrets.token_urlsafe(48)
    try:
        key_file.write_text(generated, encoding="utf-8")
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    app_logger.log_warning(
        "SECRET_KEY 未配置或仍为占位值；已生成随机密钥并保存到 backend/.secret_key。"
        "生产环境请显式设置 SECRET_KEY。"
    )
    return generated


SECRET_KEY = _resolve_secret_key()
NEW_TOKEN_HEADER = "X-New-Access-Token"

# 使用pbkdf2_sha256作为密码哈希方案（更稳定，不依赖bcrypt版本）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# 只读请求允许匿名：该 scheme 在缺少 token 时不抛 401
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    username: str
    email: str
    full_name: str
    role: str
    department: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    # 确保密码不超过72字节（bcrypt限制）
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def maybe_refresh_token(token: str) -> Optional[str]:
    """静默续期：token 有效且剩余不足 1 小时时换发新 token。

    不校验过期（过期token 直接返回 None，由正常鉴权链路返回 401）；
    续期只发生在真实使用中的会话，避免无意义的签发。
    """
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError:
        return None

    exp = payload.get("exp")
    if exp is None:
        return None
    remaining = float(exp) - datetime.now(timezone.utc).timestamp()
    if remaining <= 0 or remaining > TOKEN_REFRESH_THRESHOLD_MINUTES * 60:
        return None

    return create_access_token(
        data={"sub": payload.get("sub"), "role": payload.get("role")},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_user_from_token(token: str, db: Session) -> User:
    """JWT → User；任何失败路径统一 401（登录态唯一入口）。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
    except JWTError:
        raise _unauthorized()
    if not username:
        raise _unauthorized()

    try:
        user = db.query(User).filter(User.username == username).first()
    except Exception as e:
        print(f"Database query error in get_current_user: {e}")
        raise _unauthorized()
    if user is None:
        raise _unauthorized()
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户（强制登录）。"""
    return _resolve_user_from_token(token, db)


# ── RBAC 策略 ────────────────────────────────────────────────────────────────
# WRITE_ROLE_POLICY / WRITE_METHODS / READ_* 由本体生成物 security_policy.py 导入，
# 唯一事实源为 ontology/src/security.ttl。不要在路由里硬编码权限矩阵。
def _domain_of(request: Request) -> str:
    """从 /api/<domain>/... 提取域；非 /api 前缀返回空串。"""
    parts = request.url.path.strip("/").split("/")
    return parts[1] if len(parts) > 1 and parts[0] == "api" else ""


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _role_of(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def require_role(*roles: str):
    """固定角色要求（供路由级 Depends 使用）。"""

    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if _role_of(current_user) == UserRole.ADMIN.value:
            return current_user
        if _role_of(current_user) not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前角色({_role_of(current_user)})无权执行该操作",
            )
        return current_user

    return _checker


async def require_write_permission(
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """按域限制写操作角色；只读请求（GET/HEAD/OPTIONS）匿名放行。

    关键：这里**不能**依赖 `get_current_user`（其 OAuth2 scheme auto_error=True
    会让匿名 GET 直接 401）。只读请求必须零鉴权代价，才能保持既有 API 契约。
    """
    if request.method not in WRITE_METHODS:
        return None
    if not token:
        raise _unauthorized("未提供访问令牌")
    current_user = _resolve_user_from_token(token, db)
    role = _role_of(current_user)
    if role == UserRole.ADMIN.value:
        return current_user
    domain = _domain_of(request)
    allowed = WRITE_ROLE_POLICY.get(domain)
    if allowed is None:
        # fail-closed：本体未声明的域一律拒绝写操作
        raise _forbidden(f"域「{domain}」未纳入写权限策略，默认拒绝")
    if role not in allowed:
        raise _forbidden(f"当前角色({role})无权在「{domain}」域执行写操作")
    return current_user


async def require_read_permission(
    request: Request,
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """按域限制 GET 读权限。

    本体 ``:anonymousRead true`` 的域直接放行（保持既有演示/冒烟契约）；
    其余域必须登录且角色命中 :readRole。ADMIN 恒通过。
    """
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        return None
    domain = _domain_of(request)
    if domain in READ_OPEN_DOMAINS:
        return None
    if not token:
        raise _unauthorized("未提供访问令牌")
    current_user = _resolve_user_from_token(token, db)
    role = _role_of(current_user)
    allowed = READ_ROLE_POLICY.get(domain)
    if role == UserRole.ADMIN.value or (allowed is not None and role in allowed):
        return current_user
    raise _forbidden(f"当前角色({role})无权读取「{domain}」域数据")


def _log_login(
    request: Request,
    db: Session,
    username: str,
    role: str | None,
    status_value: LoginStatus,
    message: str,
) -> None:
    """登录日志写入（失败不影响登录流程）。"""
    try:
        db.add(LoginLog(
            username=username,
            role=role,
            login_status=status_value,
            message=message[:300],
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
            login_time=datetime.now(),
        ))
        db.commit()
    except Exception as exc:  # pragma: no cover
        db.rollback()
        app_logger.log_error("登录日志写入失败", error=exc, username=username)


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    role_value: str | None = None
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 验证密码
        try:
            password_valid = verify_password(form_data.password, user.password_hash)
        except Exception as e:
            # 如果密码验证过程出错，记录错误但不暴露详细信息
            app_logger.log_error("密码验证失败", error=e, username=form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not password_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive"
            )
        
        # 创建访问令牌
        try:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
            access_token = create_access_token(
                data={"sub": user.username, "role": role_value},
                expires_delta=access_token_expires
            )
            _log_login(request, db, user.username, role_value, LoginStatus.SUCCESS, "登录成功")
        except Exception as e:
            app_logger.log_error("访问令牌签发失败", error=e, username=form_data.username)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as exc:
        _log_login(request, db, form_data.username, role_value, LoginStatus.FAIL, str(exc.detail))
        raise
    except Exception as e:
        # 仅服务端记录内部错误，绝不回传 str(e)（避免泄露栈/DB 细节）
        app_logger.log_error("登录流程异常", error=e, username=form_data.username)
        _log_login(request, db, form_data.username, role_value, LoginStatus.FAIL, "登录流程异常")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "department": current_user.department
    }

