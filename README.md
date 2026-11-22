# DIERP（ERP 系统）

> PCB 制造行业轻量化 ERP：以 **领域本体为单一事实源**，覆盖「销售报价 → 工程数据 → 计划排程 → 生产执行 → 物料/质量 → 业财闭环」全流程的可运行原型。
> 原 README 中「FastAPI 微服务 + 四大业务模块」的描述已过时：当前后端为**单体 FastAPI 应用 + 分层服务**，业务域已扩展到计划/财务/库存/质量/驾驶舱等十余个域。

## 1. 项目概述

- **定位**：验证 PCB 制造核心业务流程的，同时作为「模型 / 本体驱动」架构的落地样例。
- **业务闭环**：SD 报价与订单 → ENG 工程数据（BOM / 工艺 / MI）→ PP/MM 生产与物料 → QMS 质量与追溯 → 财务总账与库存计价 → 6 个驾驶舱的经营分析。
- **架构特点**：
  - 本体（`ontology/src/*.ttl` + `ontology/model/*.yaml`）是枚举、实体、约束、安全策略的**唯一事实源**；
  - 后端模型、前端类型与 TS 枚举由生成器产出，CI 用**双栈门禁**检查生成物漂移；
  - RBAC 写/读权限矩阵源自 `security.ttl`，同时驱动后端 Python 策略与前端 TS 策略，并逐域比对（parity）；
  - 前端内置纯内存 **Mock 演示模式**与**单文件离线包**，无需后端即可演示。

## 2. 技术架构

| 层次 | 技术 |
| --- | --- |
| 前端 | React 18 + TypeScript 5 + Vite 5；Ant Design 5 + Tailwind CSS 3；react-router-dom 6、Zustand、axios；Vitest + Playwright |
| 后端 | Python 3.12 + FastAPI 0.135 + Uvicorn；Pydantic 2；SQLAlchemy 2 + Alembic；PyJWT + passlib；Redis / Celery（已依赖） |
| 数据库 | PostgreSQL 15（`hserp_mvp`）；ORM 统一访问，仅建库/枚举维护脚本使用 psycopg2 直连 |
| 语义层 | OWL（`erp-ontology.ttl`）+ SHACL（`shapes.ttl`）+ SWRL 规则 + YAML 运营模型；rdflib / pyshacl / owlrl / n3 |
| 容器化 | Docker Compose：PostgreSQL + 后端 + 前端（多阶段构建内嵌 Nginx，仅暴露 8080） |
| CI / 门禁 | GitHub Actions（`.github/workflows/gate.yml`）；聚合门禁 `backend/scripts/gate.py`（默认 15 项，可选 `--with-db` / `--with-e2e`） |

> 说明：后端是**单体应用**（`backend/api/main.py` 统一挂载 14 个路由），不存在独立 API 网关进程或微服务部署；`backend/package.json` 仅为遗留清单，不是 Node 服务。

## 3. 项目结构

```text
erp/
├── backend/                     # 后端（FastAPI 单体）
│   ├── api/
│   │   ├── main.py              # 应用入口：中间件 / 异常处理 / 路由装配
│   │   └── routers/             # auth, users, sd, eng, pp, mm, planning, qms,
│   │                            # traceability, dashboard, purchase, finance, admin, system
│   ├── common/
│   │   ├── database/            # SQLAlchemy engine / SessionLocal / get_db
│   │   ├── models/              # 数据模型：base, user, admin, audit, dashboard,
│   │                            # eng, mm, pp, sd, planning（规划模型为生成物）
│   │   └── utils/               # 业务规则、编号生成、权限、工作流、事务、安全策略（生成物）等
│   ├── services/                # 领域服务层
│   │   ├── planning/            # APS / MPS / MRP / 齐套 / 成本 / EAM / QMS / 追溯 / 驾驶舱引擎
│   │   ├── finance/             # 总账引擎、会计期间、财务种子数据
│   │   ├── inventory/           # 移动加权计价、库存种子数据
│   │   ├── dashboard/           # 驾驶舱告警
│   │   ├── system/              # 系统管理种子数据
│   │   └── *.py                 # 销售订单 / 生产订单 / 单据映射服务
│   ├── ontology/                # 后端生成器：generate_models.py / generate_security.py
│   ├── migrations/              # Alembic 迁移（head: c3d4e5f6a8b9 驾驶舱规则）
│   ├── scripts/                 # gate.py 聚合门禁 + parity 校验 + 冒烟/探针 + 演示数据脚本
│   ├── tests/                   # pytest（SQLite 内存库，无需真实 PostgreSQL）
│   └── requirements.txt
├── frontend/                    # 前端（React + Vite）
│   ├── src/
│   │   ├── components/          # 布局（AppLayout/Sidebar/Header/PageTabs）与通用组件
│   │   ├── pages/               # sd, eng, pp, mm, planning, aps, cost, qms, eam,
│   │   │                        # finance, dashboard, traceability, admin, auth
│   │   ├── services/            # axios 统一请求封装（令牌静默续期）
│   │   ├── stores/              # Zustand：auth / theme / ui / order / material
│   │   ├── mock/                # 无后端演示：适配器 + handlers + snapshot.json
│   │   ├── types/               # 由本体生成的类型 / 枚举（*.generated.ts）
│   │   └── theme/               # 亮/暗主题令牌
│   ├── e2e/                     # Playwright 核心链路测试
│   ├── mock-tests/              # 演示 handler 测试
│   └── scripts/                 # Mock RBAC 校验 / 演示包构建
├── ontology/                    # 语义层（单一事实源）
│   ├── src/                     # erp-ontology.ttl / shapes.ttl / security.ttl / rules.swrl / mappings.json
│   ├── model/                   # admin.yaml / dashboard.yaml / planning.yaml 运营模型
│   ├── data/demo.ttl            # 演示本体实例
│   ├── generated/types.ts       # 由 mappings.json 生成的 TS 枚举
│   └── scripts/                 # 类型生成 + Node/Python 双栈一致性校验
├── docs/                        # 建模规范、ER/工作流/状态机/类图/用例（138 md + 70 puml）
├── 需求/                        # 需求规格说明书（1.3/1.4/1.5）与 23 份 BPMN 流程图
├── docker/                      # 后端/前端 Dockerfile 与 Nginx 配置
├── .github/workflows/gate.yml   # CI：hermetic gate + 浏览器 E2E
├── docker-compose.yml           # 一键容器化启动
└── DIERP-demo-说明.txt          # 离线演示包使用说明
```

## 4. 核心业务域

### 4.1 价值链主流程
- **SD 销售与分销**：客户建档、报价三级审核、销售订单与订单评审、发货、销售发票、红字冲回。
- **ENG 工程管理**：BOM（多层展开 / 循环检查）、工艺路线、MI、生产版本。
- **PP 生产执行**：工作中心、生产订单、工序报工、生产订单关闭、LOT 卡、进度看板。
- **MM 物料管理**：物料主数据、采购单、生产领料（含原料批次追溯）、库存盘点/调拨、移动加权计价。

### 4.2 计划与运营
- **计划域**：MPS / MRP / 计划订单 / 需求追溯 / 异常 / 齐套 / 计划参数（模型由本体 YAML 生成）。
- **APS 工作台**：高级排程、主数据、排程结果可视化。
- **QMS 质量**：检验与质量快照、质量门禁；**追溯域**：领料 → 批次 → 采购单 → 供应商。
- **成本管理**：实际成本计算与成本工作台。

### 4.3 业财与经营分析
- **财务**：销售/供应商发票、收付款单、核销、会计期间与凭证（总账引擎 GL）；发票/收款红字冲回。
- **库存计价**：移动加权估值流水，盘点差异自动生成调整凭证。
- **6 个驾驶舱**：驾驶舱中心、管理驾驶舱、生产驾驶舱、生产进度看板、财务驾驶舱、销售驾驶舱；KPI 下钻 + 本体 `DashboardRule` 阈值预警。
- **领域工作台**：计划 / APS / 成本 / 质量 / 设备集中入口。

### 4.4 系统与安全
- 用户 / 角色 / 部门 / 菜单 / 系统参数 / 操作审计日志 / 登录日志；数据导入导出（JSON/CSV，幂等）。
- 本体驱动的 RBAC：`security.ttl` → 后端 `security_policy.py` + 前端 `authorization.generated.ts`，双栈 parity 校验，写操作 fail-closed。
- JWT 鉴权（HS256）+ 静默续期 + 请求 ID 贯穿审计日志；表单级权限与接口级权限一致。

## 5. 本体驱动架构（重要）

- **单一事实源**：枚举来自 `ontology/src/mappings.json`；实体字段来自 `ontology/model/*.yaml`；语义约束来自 `shapes.ttl`；派生规则来自 `rules.swrl`；安全策略来自 `security.ttl`。
- **生成物不可手改**：`backend/common/models/planning.py`、`backend/common/utils/security_policy.py`、`frontend/src/types/planning.generated.ts`、`frontend/src/types/authorization.generated.ts`、`ontology/generated/types.ts` 均由生成器产出（文件头有 `GENERATED FILE` 标记）。
- **常用生成/校验命令**（在仓库根目录）：
  ```bash
  cd ontology && python scripts/generate-types.py && npm run check && python scripts/validate-consistency.py && cd ..
  python backend/ontology/generate_models.py --check
  python backend/ontology/generate_security.py --check
  ```

## 6. 快速开始

### 6.1 环境要求
- Python 3.12（CI 版本），Node.js 20+，PostgreSQL 15；Docker Compose（可选）。

### 6.2 后端启动

> Windows 用户：`pip` 不可用时改用 `py -m pip`。

**方式一：启动脚本（推荐，Windows）**
```powershell
cd backend
.\start.ps1          # 或 CMD: start.bat
```

**方式二：手动启动**
```bash
cd backend
pip install -r requirements.txt
# 在 backend/ 下创建 .env 并填写数据库连接信息（参考 docs/快速开始.md）：
# DATABASE_URL=postgresql://postgres:你的密码@localhost:5432/hserp_mvp
# SECRET_KEY=your-secret-key-change-in-production
# ALGORITHM=HS256

# 首次运行：建库 + 初始化表 + 工作流 + Alembic 迁移
py create_database.py
py init_db.py
alembic upgrade head

# 启动服务（Windows PowerShell）
$env:PYTHONPATH = ".."
py -m uvicorn api.main:app --reload
# Linux/Mac: PYTHONPATH=.. uvicorn api.main:app --reload
```
- API 文档：<http://localhost:8000/docs>
- 数据库初始化细节见 `docs/数据库设置指南.md`。

### 6.3 前端启动
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000，/api 代理到 localhost:8000
```

### 6.4 容器化启动（一条命令起全栈）
```bash
docker compose up --build
# 前端: http://localhost:8080   后端: 容器内 8000，Nginx 反代 /api
```
首次容器启动需自行执行建表/迁移与演示数据初始化（见 `docs/部署指南.md`）。

### 6.5 离线演示（无需数据库/后端）
```bash
cd frontend && npm run dev:mock       # Mock 模式 http://localhost:3100
npm run build:offline                # 生成仓库根目录 DIERP-demo.html（单文件离线包）
```
详见 `DIERP-demo-说明.txt`：演示数据快照含 9 个角色账号，统一密码 `admin123`，支持「重置演示数据」。

### 6.6 默认账户
- 真机版：管理员 `admin` / `admin123`（生产环境请立即修改）。
- 演示版：`admin`、`yewuyuan`、`xiaojingli`、`gongchengyuan`、`jihuayuan`、`shengchanyuan`、`cangkuyuan`、`caiwuyuan`、`zongjingli`，密码统一 `admin123`。

## 7. 测试与质量门禁

```bash
# 全量确定性门禁（本体 5 项 + 后端 4 项 + 前端 5 项，无需数据库）
python backend/scripts/gate.py
python backend/scripts/gate.py --with-db     # 追加 21 个 smoke + 7 个 probe（需 PostgreSQL）
python backend/scripts/gate.py --with-e2e    # 追加 Playwright E2E（需前端 dev server）

# 单独运行
cd backend && pytest -q
cd frontend && npm run lint && npm test && npm run test:e2e
```
- 门禁内容：本体类型/一致性/生成物/安全策略漂移、pytest、Alembic check、demo/RBAC parity、前端 tsc/eslint/vitest/mock RBAC/handlers/build。
- CI：`.github/workflows/gate.yml`（push 到 master/main 与 PR 触发），E2E job 使用 PostgreSQL service 并 reset demo 数据。

## 8. 文档导航

| 目录 / 文件 | 内容 |
| --- | --- |
| `ontology/README.md` | 本体单一事实源规则、生成命令、禁止手改清单 |
| `docs/ERP系统 - API模型（OpenAPI 3）.md` 等 | API / 服务 / 数据 / 事件 / 状态机 / 工作流建模规范 |
| `docs/快速开始.md`、`部署指南.md`、`故障排除.md` | 上手、部署与排障 |
| `docs/演示环境发布指南.md`、`演示脚本-10分钟.md` | 演示流程与发布 |
| `docs/系统完善度分析-20261119.md`、`代码Review-N1-N4-20261119.md` | 现状审查与演进记录 |
| `需求/ERP系统MVP版本需求规格说明书1.5.md` | 需求规格（BPMN 流程图同目录） |

## 9. 开发状态

- [x] 项目架构、数据库模型、编号生成器
- [x] SD / ENG / PP / MM 主流程与工作流引擎
- [x] 前端界面、用户认证、RBAC 与细粒度权限
- [x] 表单创建/编辑、报价三级审核 / 订单评审 / 月结门禁
- [x] JSON/CSV 数据导入导出、审计日志与操作留痕
- [x] 6 个驾驶舱、计划/APS/成本/质量/设备工作台
- [x] 业务规则补全：客户额度 / 工作中心产能 / 多层 BOM / 循环检查
- [x] 原料批次追溯、收款单与发票红字冲回、登录态静默续期
- [x] 本体驱动安全策略 + 双栈门禁 + 容器化 + 聚合门禁 / CI
- [x] 财务与库存演示闭环、单文件离线演示包
