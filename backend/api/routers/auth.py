"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from backend.common.database.base import get_db
from backend.common.models.user import User, UserRole
import os

router = APIRouter()

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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


# ── RBAC：按域的写操作权限门（GET 不受限，保持既有只读行为） ──────────────
# 策略：域前缀 → 允许执行写操作（POST/PUT/DELETE/PATCH）的角色集合。
# ADMIN 恒通过；未纳入策略的域（auth/dashboard/traceability 等）不限制。
WRITE_ROLE_POLICY: dict[str, set[str]] = {
    "sd": {"SALES", "SALES_MANAGER", "GENERAL_MANAGER", "ADMIN"},
    "eng": {"ENGINEER", "GENERAL_MANAGER", "ADMIN"},
    "pp": {"PRODUCTION", "PLANNER", "GENERAL_MANAGER", "ADMIN"},
    "mm": {"WAREHOUSE", "PRODUCTION", "PLANNER", "GENERAL_MANAGER", "ADMIN"},
    "planning": {"PLANNER", "GENERAL_MANAGER", "ADMIN"},
    "qms": {"PRODUCTION", "PLANNER", "GENERAL_MANAGER", "ADMIN"},
    "purchase": {"WAREHOUSE", "PRODUCTION", "PLANNER", "GENERAL_MANAGER", "ADMIN"},
    "users": {"ADMIN"},
}

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


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
    parts = request.url.path.strip("/").split("/")
    domain = parts[1] if len(parts) > 1 and parts[0] == "api" else ""
    allowed = WRITE_ROLE_POLICY.get(domain)
    if allowed is None:
        return current_user
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"当前角色({role})无权在「{domain}」域执行写操作",
        )
    return current_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
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
            print(f"Password verification error: {e}")
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
        except Exception as e:
            print(f"Token creation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token"
            )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        # 捕获所有其他异常并记录
        print(f"Login error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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

