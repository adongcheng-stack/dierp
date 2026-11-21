"""登录态静默续期单元测试。"""
from datetime import timedelta

from backend.api.routers.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWTError,
    SECRET_KEY,
    ALGORITHM,
    create_access_token,
    jwt,
    maybe_refresh_token,
)


def test_long_lived_token_not_refreshed():
    token = create_access_token({"sub": "admin", "role": "ADMIN"}, timedelta(minutes=480))
    assert maybe_refresh_token(token) is None


def test_near_expiry_token_is_refreshed():
    token = create_access_token({"sub": "admin", "role": "ADMIN"}, timedelta(minutes=30))
    renewed = maybe_refresh_token(token)
    assert renewed is not None
    assert renewed != token
    payload = jwt.decode(renewed, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"
    assert payload["role"] == "ADMIN"
    # 续期后恢复完整 8h 有效期
    from datetime import datetime, timezone
    remaining = payload["exp"] - datetime.now(timezone.utc).timestamp()
    assert ACCESS_TOKEN_EXPIRE_MINUTES * 60 - remaining < 60


def test_expired_or_invalid_token_not_refreshed():
    expired = create_access_token({"sub": "admin"}, timedelta(seconds=-10))
    assert maybe_refresh_token(expired) is None
    assert maybe_refresh_token("not-a-jwt") is None
