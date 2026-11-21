"""总账自动分录映射表（配置化常量，P2 demo 口径）。

科目表 8 个一级科目（均为明细科目），GL_RULES 定义业务事件 → 借/贷科目；
金额口径由调用方（挂分录处）决定：
  - SALES_INVOICE_ISSUED / SUPPLIER_INVOICE_CONFIRMED / SUPPLIER_PAYMENT_PAID / RECEIPT_PAID → 单据金额
  - SALES_DELIVERY_SHIPPED / MATERIAL_ISSUE / PRODUCTION_COMPLETE → 数量 × 标准成本（成本域 standard_cost）
  - PURCHASE_RECEIPT 不单独入账（与发票合并，demo 简化）
"""

# 一级科目种子：(科目编码, 科目名称, 类别)
GL_ACCOUNTS: list[tuple[str, str, str]] = [
    ("1002", "银行存款", "ASSET"),
    ("1122", "应收账款", "ASSET"),
    ("1405", "库存商品", "ASSET"),
    ("2202", "应付账款", "LIABILITY"),
    ("4001", "实收资本", "EQUITY"),
    ("3131", "本年利润", "EQUITY"),
    ("5001", "生产成本", "EXPENSE"),
    ("6001", "主营业务收入", "REVENUE"),
    ("6401", "主营业务成本", "EXPENSE"),
    ("6402", "存货差异", "EXPENSE"),
]

# 业务事件 → (借方科目, 贷方科目)
GL_RULES: dict[str, tuple[str, str]] = {
    "SALES_INVOICE_ISSUED": ("1122", "6001"),
    "SALES_INVOICE_REVERSED": ("6001", "1122"),
    "SALES_DELIVERY_SHIPPED": ("6401", "1405"),
    "SUPPLIER_INVOICE_CONFIRMED": ("1405", "2202"),
    "SUPPLIER_PAYMENT_PAID": ("2202", "1002"),
    "RECEIPT_PAID": ("1002", "1122"),
    "RECEIPT_PAID_REVERSE": ("1122", "1002"),
    "MATERIAL_ISSUE": ("5001", "1405"),
    "STOCK_ADJUST": ("5001", "1405"),
    "PRODUCTION_COMPLETE": ("1405", "5001"),
}

# P2 上线不回补历史单据；期初以「银行存款/实收资本」一笔 opening entry 表达（demo 口径）
