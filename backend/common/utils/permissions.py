"""
权限检查工具
"""
from fastapi import HTTPException, status
from backend.common.models.user import User, UserRole
from typing import List, Union


def require_role(user: User, required_role: UserRole, error_message: str = None):
    """
    要求用户具有指定角色，ADMIN角色可以绕过所有限制
    
    Args:
        user: 当前用户
        required_role: 要求的角色
        error_message: 自定义错误消息
    
    Raises:
        HTTPException: 如果用户没有权限
    """
    # ADMIN角色拥有所有权限
    if user.role == UserRole.ADMIN:
        return
    
    if user.role != required_role:
        message = error_message or f"需要角色 {required_role.value} 才能执行此操作"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


def require_any_role(user: User, required_roles: List[UserRole], error_message: str = None):
    """
    要求用户具有指定角色列表中的任意一个角色，ADMIN角色可以绕过所有限制
    
    Args:
        user: 当前用户
        required_roles: 要求的角色列表
        error_message: 自定义错误消息
    
    Raises:
        HTTPException: 如果用户没有权限
    """
    # ADMIN角色拥有所有权限
    if user.role == UserRole.ADMIN:
        return
    
    if user.role not in required_roles:
        role_names = ", ".join([role.value for role in required_roles])
        message = error_message or f"需要以下角色之一才能执行此操作: {role_names}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


def require_admin(user: User, error_message: str = None):
    """
    要求用户是管理员
    
    Args:
        user: 当前用户
        error_message: 自定义错误消息
    
    Raises:
        HTTPException: 如果用户不是管理员
    """
    if user.role != UserRole.ADMIN:
        message = error_message or "只有管理员可以执行此操作"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )


def is_admin(user: User) -> bool:
    """
    检查用户是否是管理员
    
    Args:
        user: 当前用户
    
    Returns:
        bool: 如果是管理员返回True
    """
    return user.role == UserRole.ADMIN


def has_role(user: User, role: UserRole) -> bool:
    """
    检查用户是否具有指定角色，ADMIN角色被视为拥有所有角色
    
    Args:
        user: 当前用户
        role: 要检查的角色
    
    Returns:
        bool: 如果用户具有该角色或为ADMIN返回True
    """
    if user.role == UserRole.ADMIN:
        return True
    return user.role == role


def has_any_role(user: User, roles: List[UserRole]) -> bool:
    """
    检查用户是否具有指定角色列表中的任意一个角色，ADMIN角色被视为拥有所有角色
    
    Args:
        user: 当前用户
        roles: 要检查的角色列表
    
    Returns:
        bool: 如果用户具有任一角色或为ADMIN返回True
    """
    if user.role == UserRole.ADMIN:
        return True
    return user.role in roles

