"""组织架构与系统管理路由（本体 admin.yaml 生成模型 + system 域 RBAC）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.common.database.base import get_db
from backend.common.models.admin import (
    Department,
    DepartmentStatus,
    LoginLog,
    Menu,
    MenuStatus,
    RoleMenu,
    SystemParameter,
    UserRole,
)
from backend.common.models.user import User, UserRole as LegacyUserRole

router = APIRouter()

ROLE_LABELS = {
    "SALES": "销售",
    "SALES_MANAGER": "销售经理",
    "ENGINEER": "工程",
    "PLANNER": "计划",
    "PRODUCTION": "生产",
    "WAREHOUSE": "仓库",
    "FINANCE": "财务",
    "GENERAL_MANAGER": "总经理",
    "ADMIN": "系统管理员",
}


def _tree(rows: list[dict]) -> list[dict]:
    """把扁平行按 parent_id 组装为树。"""
    by_id = {row["id"]: {**row, "children": []} for row in rows}
    roots: list[dict] = []
    for row in rows:
        node = by_id[row["id"]]
        parent = by_id.get(row.get("parent_id"))
        (parent["children"] if parent else roots).append(node)
    return roots


def _dict(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _serialize(row) -> dict:
    result = {}
    for key, value in _dict(row).items():
        if isinstance(value, (datetime,)):
            value = value.isoformat()
        elif hasattr(value, "value"):
            value = value.value
        result[key] = value
    return result


# ── 部门 ──────────────────────────────────────────────────────────────────
class DepartmentPayload(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None
    level: int = 1
    department_type: str = "DEPARTMENT"
    manager: Optional[str] = None
    contact_phone: Optional[str] = None
    sort_order: int = 0
    status: str = "ACTIVE"
    established_date: Optional[str] = None
    remark: Optional[str] = None


def _apply_department(row: Department, payload: DepartmentPayload) -> None:
    for field in DepartmentPayload.model_fields:
        setattr(row, field, getattr(payload, field))


@router.get("/departments")
async def list_departments(db: Session = Depends(get_db)):
    rows = db.query(Department).filter(Department.is_deleted.is_(False)).order_by(Department.sort_order).all()
    return {"total": len(rows), "items": [_serialize(row) for row in rows]}


@router.get("/departments/tree")
async def department_tree(db: Session = Depends(get_db)):
    rows = db.query(Department).filter(Department.is_deleted.is_(False)).order_by(Department.sort_order).all()
    return _tree([_serialize(row) for row in rows])


@router.post("/departments")
async def create_department(payload: DepartmentPayload, db: Session = Depends(get_db)):
    if db.query(Department).filter(Department.code == payload.code, Department.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail=f"部门编码已存在: {payload.code}")
    row = Department(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.put("/departments/{item_id}")
async def update_department(item_id: int, payload: DepartmentPayload, db: Session = Depends(get_db)):
    row = db.query(Department).filter(Department.id == item_id, Department.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status_code=404, detail="部门不存在")
    if payload.parent_id == item_id:
        raise HTTPException(status_code=400, detail="上级部门不能是自己")
    _apply_department(row, payload)
    db.commit()
    return _serialize(row)


@router.delete("/departments/{item_id}")
async def delete_department(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Department).filter(Department.id == item_id, Department.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status_code=404, detail="部门不存在")
    if db.query(Department).filter(Department.parent_id == item_id, Department.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail="存在下级部门，无法删除")
    row.is_deleted = True
    db.commit()
    return {"deleted": item_id}


# ── 角色与菜单授权 ────────────────────────────────────────────────────────
@router.get("/roles")
async def list_roles(db: Session = Depends(get_db)):
    rows = []
    for role in UserRole:
        menu_count = db.query(RoleMenu).filter(RoleMenu.role_code == role, RoleMenu.is_deleted.is_(False)).count()
        user_count = db.query(User).filter(User.role == LegacyUserRole(role.value), User.is_active.is_(True)).count()
        rows.append({
            "code": role.value,
            "name": ROLE_LABELS.get(role.value, role.value),
            "menu_count": menu_count,
            "user_count": user_count,
        })
    return {"total": len(rows), "items": rows}


@router.get("/roles/{role_code}/menus")
async def get_role_menus(role_code: str, db: Session = Depends(get_db)):
    rows = db.query(RoleMenu).filter(
        RoleMenu.role_code == UserRole(role_code), RoleMenu.is_deleted.is_(False)
    ).all()
    return {"role": role_code, "menu_ids": [row.menu_id for row in rows]}


class MenuGrantPayload(BaseModel):
    menu_ids: list[int]


@router.post("/roles/{role_code}/menus")
async def set_role_menus(role_code: str, payload: MenuGrantPayload, db: Session = Depends(get_db)):
    try:
        role = UserRole(role_code)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"未知角色: {role_code}")
    db.query(RoleMenu).filter(RoleMenu.role_code == role).delete()
    for menu_id in set(payload.menu_ids):
        if not db.query(Menu).filter(Menu.id == menu_id, Menu.is_deleted.is_(False)).first():
            raise HTTPException(status_code=400, detail=f"菜单不存在: {menu_id}")
        db.add(RoleMenu(role_code=role, menu_id=menu_id))
    db.commit()
    return {"role": role_code, "menu_ids": payload.menu_ids}


# ── 菜单 ──────────────────────────────────────────────────────────────────
class MenuPayload(BaseModel):
    code: str
    name: str
    parent_id: Optional[int] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    menu_type: str = "MENU"
    permission: Optional[str] = None
    sort_order: int = 0
    visible: bool = True
    status: str = "ACTIVE"


@router.get("/menus")
async def list_menus(db: Session = Depends(get_db)):
    rows = db.query(Menu).filter(Menu.is_deleted.is_(False)).order_by(Menu.sort_order).all()
    return {"total": len(rows), "items": [_serialize(row) for row in rows]}


@router.get("/menus/tree")
async def menu_tree(db: Session = Depends(get_db)):
    rows = db.query(Menu).filter(Menu.is_deleted.is_(False)).order_by(Menu.sort_order).all()
    return _tree([_serialize(row) for row in rows])


@router.post("/menus")
async def create_menu(payload: MenuPayload, db: Session = Depends(get_db)):
    if db.query(Menu).filter(Menu.code == payload.code, Menu.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail=f"菜单编码已存在: {payload.code}")
    row = Menu(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.put("/menus/{item_id}")
async def update_menu(item_id: int, payload: MenuPayload, db: Session = Depends(get_db)):
    row = db.query(Menu).filter(Menu.id == item_id, Menu.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status_code=404, detail="菜单不存在")
    if payload.parent_id == item_id:
        raise HTTPException(status_code=400, detail="上级菜单不能是自己")
    for field in MenuPayload.model_fields:
        setattr(row, field, getattr(payload, field))
    db.commit()
    return _serialize(row)


@router.delete("/menus/{item_id}")
async def delete_menu(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Menu).filter(Menu.id == item_id, Menu.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status_code=404, detail="菜单不存在")
    if db.query(Menu).filter(Menu.parent_id == item_id, Menu.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail="存在下级菜单，无法删除")
    db.query(RoleMenu).filter(RoleMenu.menu_id == item_id).delete()
    row.is_deleted = True
    db.commit()
    return {"deleted": item_id}


# ── 系统参数 ──────────────────────────────────────────────────────────────
class ParamPayload(BaseModel):
    param_key: str
    param_name: str
    param_value: Optional[str] = None
    param_type: str = "STRING"
    param_desc: Optional[str] = None
    is_system: bool = False
    remark: Optional[str] = None


@router.get("/parameters")
async def list_parameters(db: Session = Depends(get_db)):
    rows = db.query(SystemParameter).filter(SystemParameter.is_deleted.is_(False)).order_by(SystemParameter.param_key).all()
    return {"total": len(rows), "items": [_serialize(row) for row in rows]}


@router.get("/parameters/key/{param_key}")
async def get_parameter(param_key: str, db: Session = Depends(get_db)):
    row = db.query(SystemParameter).filter(
        SystemParameter.param_key == param_key, SystemParameter.is_deleted.is_(False)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"参数不存在: {param_key}")
    return _serialize(row)


@router.post("/parameters")
async def create_parameter(payload: ParamPayload, db: Session = Depends(get_db)):
    if db.query(SystemParameter).filter(SystemParameter.param_key == payload.param_key, SystemParameter.is_deleted.is_(False)).first():
        raise HTTPException(status_code=400, detail=f"参数键已存在: {payload.param_key}")
    row = SystemParameter(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.put("/parameters/{item_id}")
async def update_parameter(item_id: int, payload: ParamPayload, db: Session = Depends(get_db)):
    row = db.query(SystemParameter).filter(SystemParameter.id == item_id, SystemParameter.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status_code=404, detail="参数不存在")
    for field in ParamPayload.model_fields:
        setattr(row, field, getattr(payload, field))
    db.commit()
    return _serialize(row)


@router.delete("/parameters/{item_id}")
async def delete_parameter(item_id: int, db: Session = Depends(get_db)):
    row = db.query(SystemParameter).filter(SystemParameter.id == item_id, SystemParameter.is_deleted.is_(False)).first()
    if not row:
        raise HTTPException(status_code=404, detail="参数不存在")
    if row.is_system:
        raise HTTPException(status_code=400, detail="系统内置参数不可删除")
    row.is_deleted = True
    db.commit()
    return {"deleted": item_id}


# ── 登录日志 ──────────────────────────────────────────────────────────────
@router.get("/login-logs")
async def list_login_logs(
    username: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(LoginLog).filter(LoginLog.is_deleted.is_(False))
    if username:
        query = query.filter(LoginLog.username == username)
    rows = query.order_by(LoginLog.login_time.desc(), LoginLog.id.desc()).limit(limit).all()
    return {"total": len(rows), "items": [_serialize(row) for row in rows]}
