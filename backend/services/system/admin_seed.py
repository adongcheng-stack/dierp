"""组织架构与系统管理的演示种子（幂等）。

由 demo_reset 在重建主数据时调用，保证前端 mock 与真机看到同一套组织/菜单/参数。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.common.models.admin import (
    Department,
    DepartmentStatus,
    DepartmentType,
    Menu,
    MenuStatus,
    MenuType,
    RoleMenu,
    SystemParameter,
    UserRole,
)

DEPARTMENTS = [
    ("D-ROOT", "总公司", None, 1, "COMPANY", "总经理", "0755-88880000", 0),
    ("D-SALES", "销售部", "D-ROOT", 2, "DEPARTMENT", "销售经理", "0755-88880001", 1),
    ("D-ENG", "工程部", "D-ROOT", 2, "DEPARTMENT", "工程主管", "0755-88880002", 2),
    ("D-PROD", "生产部", "D-ROOT", 2, "DEPARTMENT", "生产主管", "0755-88880003", 3),
    ("D-PROC", "工艺组", "D-PROD", 3, "TEAM", "工艺工程师", None, 1),
    ("D-MM", "物料部", "D-ROOT", 2, "DEPARTMENT", "仓库主管", "0755-88880004", 4),
    ("D-FIN", "财务部", "D-ROOT", 2, "DEPARTMENT", "财务经理", "0755-88880005", 5),
    ("D-QA", "质量部", "D-ROOT", 2, "DEPARTMENT", "质量主管", "0755-88880006", 6),
]

# code, name, path, parent_code, type, sort, permission
MENUS = [
    ("M-DASH", "仪表盘", "/", None, "DIRECTORY", 1, None),
    ("M-DASH-MAIN", "仪表盘首页", "/dashboard", "M-DASH", "MENU", 1, "dashboard:view"),
    ("M-DASH-MGMT", "经营看板", "/dashboard/management", "M-DASH", "MENU", 2, "dashboard:management"),
    ("M-SD", "销售管理", "/sd", None, "DIRECTORY", 2, None),
    ("M-SD-CUST", "客户管理", "/sd/customers", "M-SD", "MENU", 1, "sd:customer:list"),
    ("M-SD-QT", "报价单", "/sd/quotations", "M-SD", "MENU", 2, "sd:quotation:list"),
    ("M-SD-SO", "销售订单", "/sd/sales-orders", "M-SD", "MENU", 3, "sd:salesorder:list"),
    ("M-SD-DN", "发货管理", "/sd/deliveries", "M-SD", "MENU", 4, "sd:delivery:list"),
    ("M-SD-INV", "销售发票", "/sd/invoices", "M-SD", "MENU", 5, "sd:invoice:list"),
    ("M-SD-RCT", "收款单", "/sd/receipts", "M-SD", "MENU", 6, "sd:receipt:list"),
    ("M-PP", "生产计划", "/pp", None, "DIRECTORY", 3, None),
    ("M-PP-WC", "工作中心", "/pp/work-centers", "M-PP", "MENU", 1, "pp:workcenter:list"),
    ("M-PP-MO", "生产订单", "/pp/production-orders", "M-PP", "MENU", 2, "pp:productionorder:list"),
    ("M-MM", "库存管理", "/mm", None, "DIRECTORY", 4, None),
    ("M-MM-MAT", "物料管理", "/mm/materials", "M-MM", "MENU", 1, "mm:material:list"),
    ("M-MM-ISSUE", "生产领料", "/mm/material-issues", "M-MM", "MENU", 2, "mm:issue:list"),
    ("M-MM-INV", "库存台账", "/mm/inventory", "M-MM", "MENU", 3, "mm:inventory:list"),
    ("M-FIN", "财务管理", "/finance", None, "DIRECTORY", 5, None),
    ("M-FIN-ACC", "会计科目", "/finance/accounts", "M-FIN", "MENU", 1, "finance:account:list"),
    ("M-FIN-PD", "期间月结", "/finance/periods", "M-FIN", "MENU", 2, "finance:period:close"),
    ("M-SYS", "系统管理", "/admin", None, "DIRECTORY", 6, None),
    ("M-SYS-USR", "用户管理", "/admin/users", "M-SYS", "MENU", 1, "system:user:list"),
    ("M-SYS-ROL", "角色管理", "/admin/roles", "M-SYS", "MENU", 2, "system:role:list"),
    ("M-SYS-DEP", "部门管理", "/admin/departments", "M-SYS", "MENU", 3, "system:dept:list"),
    ("M-SYS-MNU", "菜单管理", "/admin/menus", "M-SYS", "MENU", 4, "system:menu:list"),
    ("M-SYS-PRM", "系统参数", "/admin/parameters", "M-SYS", "MENU", 5, "system:param:list"),
    ("M-SYS-LOG", "操作审计日志", "/admin/operation-logs", "M-SYS", "MENU", 6, "system:log:list"),
    ("M-SYS-LOGIN", "登录日志", "/admin/login-logs", "M-SYS", "MENU", 7, "system:loginlog:list"),
    ("M-SYS-EXP", "数据导入导出", "/admin/data-exchange", "M-SYS", "MENU", 8, "system:data:exchange"),
]

ROLE_MENU_CODES = {
    UserRole.ADMIN: [code for code, *_ in MENUS],
    UserRole.GENERAL_MANAGER: [code for code, *_ in MENUS],
    UserRole.SALES: ["M-DASH", "M-DASH-MAIN", "M-SD", "M-SD-CUST", "M-SD-QT", "M-SD-SO", "M-SD-DN", "M-SD-INV", "M-SD-RCT"],
    UserRole.SALES_MANAGER: ["M-DASH", "M-DASH-MAIN", "M-SD", "M-SD-CUST", "M-SD-QT", "M-SD-SO", "M-SD-DN", "M-SD-INV", "M-SD-RCT"],
    UserRole.ENGINEER: ["M-DASH", "M-DASH-MAIN", "M-PP", "M-PP-WC", "M-PP-MO"],
    UserRole.PLANNER: ["M-DASH", "M-DASH-MAIN", "M-DASH-MGMT", "M-PP", "M-PP-WC", "M-PP-MO", "M-MM", "M-MM-MAT"],
    UserRole.PRODUCTION: ["M-DASH", "M-DASH-MAIN", "M-PP", "M-PP-MO", "M-MM", "M-MM-ISSUE"],
    UserRole.WAREHOUSE: ["M-DASH", "M-DASH-MAIN", "M-MM", "M-MM-MAT", "M-MM-ISSUE", "M-MM-INV"],
    UserRole.FINANCE: ["M-DASH", "M-DASH-MAIN", "M-DASH-MGMT", "M-FIN", "M-FIN-ACC", "M-FIN-PD"],
}

PARAMS = [
    ("company.name", "公司名称", "深圳市某某电路有限公司", "STRING", "演示企业抬头", True),
    ("finance.fiscal_year_start", "财年起始月", "1", "INT", "财年开始的月份", True),
    ("finance.period.auto_close", "期间自动结账", "false", "BOOLEAN", "月结是否自动执行", False),
    ("valuation.method", "存货计价法", "MOVING_AVERAGE", "STRING", "移动加权 / 标准成本", True),
    ("security.token.expire_minutes", "令牌有效期(分钟)", "480", "INT", "演示口径 8 小时", True),
    ("demo.reset.enabled", "演示数据可重置", "true", "BOOLEAN", "是否在菜单显示重置入口", False),
]


def seed_admin_demo(db: Session) -> None:
    """幂等写入部门、菜单、角色授权与系统参数。"""
    # 部门
    code_to_dept: dict[str, Department] = {}
    for code, name, parent_code, level, dtype, manager, phone, sort in DEPARTMENTS:
        row = db.query(Department).filter(Department.code == code, Department.is_deleted.is_(False)).first()
        if row is None:
            row = Department(code=code, status=DepartmentStatus.ACTIVE, department_type=DepartmentType.DEPARTMENT)
            db.add(row)
        row.name = name
        row.level = level
        row.department_type = DepartmentType(dtype)
        row.manager = manager
        row.contact_phone = phone
        row.sort_order = sort
        row.status = DepartmentStatus.ACTIVE
        code_to_dept[code] = row
    db.flush()
    for code, _name, parent_code, *_rest in DEPARTMENTS:
        if parent_code:
            code_to_dept[code].parent_id = code_to_dept[parent_code].id

    # 菜单
    code_to_menu: dict[str, Menu] = {}
    for code, name, path, parent_code, mtype, sort, permission in MENUS:
        row = db.query(Menu).filter(Menu.code == code, Menu.is_deleted.is_(False)).first()
        if row is None:
            row = Menu(code=code, status=MenuStatus.ACTIVE, menu_type=MenuType.MENU)
            db.add(row)
        row.name = name
        row.path = path
        row.menu_type = MenuType(mtype)
        row.permission = permission
        row.sort_order = sort
        row.visible = True
        row.status = MenuStatus.ACTIVE
        code_to_menu[code] = row
    db.flush()
    for code, _name, _path, parent_code, *_rest in MENUS:
        if parent_code:
            code_to_menu[code].parent_id = code_to_menu[parent_code].id

    # 角色-菜单授权（全量替换，保证幂等）
    db.query(RoleMenu).delete()
    for role, codes in ROLE_MENU_CODES.items():
        for code in codes:
            db.add(RoleMenu(role_code=role, menu_id=code_to_menu[code].id))

    # 系统参数
    for key, name, value, ptype, desc, is_system in PARAMS:
        row = db.query(SystemParameter).filter(SystemParameter.param_key == key, SystemParameter.is_deleted.is_(False)).first()
        if row is None:
            row = SystemParameter(param_key=key)
            db.add(row)
        row.param_name = name
        row.param_value = value
        row.param_type = ptype
        row.param_desc = desc
        row.is_system = is_system

    db.flush()
