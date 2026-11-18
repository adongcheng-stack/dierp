"""
用户管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from backend.common.database.base import get_db
from backend.common.models.user import User, UserRole
from backend.api.routers.auth import get_current_user, get_password_hash, verify_password

router = APIRouter()


# Pydantic模型
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    department: Optional[str]
    is_active: bool
    phone: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]


class RoleInfo(BaseModel):
    role: str
    name: str
    description: str


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建用户（仅管理员）"""
    # 检查权限
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以创建用户"
        )
    
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户名已存在: {user.username}"
        )
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"邮箱已存在: {user.email}"
        )
    
    try:
        # 创建用户
        password_hash = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            password_hash=password_hash,
            full_name=user.full_name,
            role=user.role,
            department=user.department,
            phone=user.phone,
            is_active=user.is_active,
            created_by=current_user.username
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        print(f"创建用户错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表（仅管理员）"""
    try:
        # 检查权限
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以查看用户列表"
            )
        
        query = db.query(User).filter(User.is_deleted == False)  # 只查询未删除的用户
        
        if role:
            # 将字符串转换为枚举类型
            try:
                role_enum = UserRole(role)
                query = query.filter(User.role == role_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的角色: {role}"
                )
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # 按创建时间倒序排列，限制返回数量
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return users
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取用户列表错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户详情（仅管理员或本人）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户不存在: {user_id}"
        )
    
    # 检查权限：管理员或本人
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此用户信息"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新用户信息（仅管理员或本人）"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户不存在: {user_id}"
        )
    
    # 检查权限：管理员或本人
    is_admin = current_user.role == UserRole.ADMIN
    is_self = current_user.id == user_id
    
    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此用户信息"
        )
    
    # 非管理员不能修改角色和激活状态
    if not is_admin:
        if user_update.role is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改用户角色"
            )
        if user_update.is_active is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改用户激活状态"
            )
    
    try:
        # 更新字段
        if user_update.email is not None:
            # 检查邮箱是否已被其他用户使用
            existing_email = db.query(User).filter(
                User.email == user_update.email,
                User.id != user_id
            ).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"邮箱已被使用: {user_update.email}"
                )
            db_user.email = user_update.email
        
        if user_update.password is not None:
            db_user.password_hash = get_password_hash(user_update.password)
        
        if user_update.full_name is not None:
            db_user.full_name = user_update.full_name
        
        if user_update.role is not None and is_admin:
            db_user.role = user_update.role
        
        if user_update.department is not None:
            db_user.department = user_update.department
        
        if user_update.phone is not None:
            db_user.phone = user_update.phone
        
        if user_update.is_active is not None and is_admin:
            db_user.is_active = user_update.is_active
        
        db_user.updated_by = current_user.username
        db.commit()
        db.refresh(db_user)
        return db_user
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"更新用户错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户失败: {str(e)}"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除用户（仅管理员，软删除）"""
    # 检查权限
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除用户"
        )
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户不存在: {user_id}"
        )
    
    # 不能删除自己
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )
    
    try:
        # 软删除
        db_user.is_deleted = True
        db_user.is_active = False
        db_user.updated_by = current_user.username
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"删除用户错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除用户失败: {str(e)}"
        )


@router.get("/roles", response_model=List[RoleInfo])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有角色列表"""
    # 检查权限
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以查看角色列表"
        )
    
    roles = [
        RoleInfo(role="SALES", name="销售", description="销售业务人员"),
        RoleInfo(role="SALES_MANAGER", name="销售经理", description="销售部门经理，负责报价单审核"),
        RoleInfo(role="ENGINEER", name="工程", description="工程技术人员"),
        RoleInfo(role="PLANNER", name="计划", description="生产计划人员"),
        RoleInfo(role="PRODUCTION", name="生产", description="生产操作人员"),
        RoleInfo(role="WAREHOUSE", name="仓库", description="仓库管理人员"),
        RoleInfo(role="FINANCE", name="财务", description="财务人员，负责报价单财务审核"),
        RoleInfo(role="GENERAL_MANAGER", name="总经理", description="总经理，负责最终审批"),
        RoleInfo(role="ADMIN", name="系统管理员", description="系统管理员，拥有所有权限"),
    ]
    
    return roles


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    return current_user

