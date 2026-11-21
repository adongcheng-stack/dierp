# Night State
## Current Task
（空）

## Pending Tasks
- [ ] QMS 高级特性（SPC / 8D / 供应商质量评分）—— 规划内明确暂缓
- [x] anyio 3.7.1 → 4.9.0（pytest 57 + E2E 5/5 回归通过）
- [ ] starlette 0.52.1 → 1.x（等待 FastAPI 兼容版本）
- [x] 报价试算端点规范化：/sd/quotations/preview-details（旧路径保留兼容）

## 交接摘要（2026-11-21，本体驱动安全加固 + 工程化 + 缺口闭环）

参考 `D:\project\mes\DevLib\trunk` 的本体驱动模式（本体 → 生成物 → 门禁），本轮完成：

### 1. P0 安全（本体驱动）
- 新增 `ontology/src/security.ttl`：角色、访问域、写/读权限矩阵、JWT 配置作为唯一事实源；SHACL 形状保护本体自身。
- 新增生成器 `backend/ontology/generate_security.py`（支持 `--check` 漂移门禁），生成：
  - `backend/common/utils/security_policy.py`（后端策略数据）
  - `frontend/src/types/authorization.generated.ts`（mock 同构策略）
- 重构 `auth.py`：策略改为从生成物导入；写门 fail-closed（未声明域默认拒绝）；新增 `require_read_permission`；JWT 占位默认值改为自动生成随机密钥（`backend/.secret_key`，已 gitignore）；登录异常不再回传 `str(e)`。
- 补齐 finance 域写权限（FINANCE/GENERAL_MANAGER/ADMIN），users/admin 域读权限仅 ADMIN。
- 前端 mock 同步消费生成物并实现同样门控；`api.ts` 增加 403 统一文案。
- JWT 库从 `python-jose` 迁移到 `PyJWT==2.12.0`，消除无安全修复的 ecdsa 传递依赖。

### 2. P1 工程化 / 可维护性
- 新增聚合门禁 `python backend/scripts/gate.py`（13 项：本体双栈 + 策略漂移 + pytest + alembic check + 双 parity + tsc/eslint/vitest/mock RBAC/handlers/build）。
- 新增 `.github/workflows/gate.yml`（Windows CI，自动跑门禁）。
- 修复 `npm run lint`：补 `.eslintrc.cjs`，清理失效 eslint-disable 注释、全角空格、case 声明等；lint 现已纳入门禁。
- 前端测试从 2 文件 10 例扩到 4 文件 19 例（新增错误处理 + 生成策略测试）。
- 修复构建 CSS 告警根因：mock handlers 里正则字面量 `/[-:T]/g` 被 Tailwind 误判为任意值类，改为 `/[\u002d:T]/g`，构建告警归零。

### 3. P1 文档缺口闭环
- 审计日志：`OperationLog` 模型 + Alembic `9c0d1e2f3a4b` + 请求 ID/静默续期/审计中间件 + ADMIN 查询端点 + 前端「操作审计日志」页面 + mock 同构。
- 数据导入导出：ADMIN 端点 `GET/POST /api/admin/{export,import}/{entity}`（JSON/CSV，自然键幂等）+ 前端「数据导入导出」页面 + 测试。
- 发票侧红字冲回：`POST /sd/invoices/{no}/reverse`（本体新增 `INVOICE_REVERSE`/`SALES_INVOICE_REVERSED` 枚举 + GL 红字规则 + Alembic `a1b2c3d4e5f7`）+ 前端按钮 + mock 同构 + 测试。

### 4. P2 细节
- 修复 `mm.py` / `valuation.py` 的 `__import__` 动态导入为显式 import。
- 补齐容器化：`docker/backend.Dockerfile`、`docker/frontend.Dockerfile`、`docker/nginx.conf`、`docker-compose.yml`、`.dockerignore`。
- `.gitignore` 增加 `.secret_key`、`dist-gate/`、Playwright 报告等。

### 门禁状态（全绿）
- 聚合门禁 `python backend/scripts/gate.py`：**13/13 PASS**
- 后端 pytest：**52 passed**（含 11 项新增安全/审计/红冲/导入导出回归）
- 本体双栈校验 + 策略漂移检查：全绿
- alembic head：`a1b2c3d4e5f7`，check 无漂移
- 前端：tsc / eslint / vitest 19 / mock RBAC / handlers 29 / build 全绿
- E2E（普通 dev + 后端 8000）：**5/5 passed**

### 备注
- 本地数据库已执行 `alembic upgrade head`（两条纯增量迁移）。
- `backend/.secret_key` 为本地随机密钥，已 gitignore，生产环境请用环境变量 SECRET_KEY 覆盖。
- `frontend/dist-offline/` 仍为用户原有未提交目录，本轮未触碰。
- 本轮改动尚未提交（便于人工审阅）。

## 追加（2026-11-21 下午）：组织架构管理体系

参照 MES `system` 域落地完整组织架构与系统管理，仍沿用本体驱动链路：

- 本体：`ontology/src/security.ttl` 新增 `system` 域（写/读均仅 ADMIN）；`ontology/model/admin.yaml` 定义 Department / Menu / RoleMenu / SystemParameter / LoginLog 五个实体；`mappings.json` 新增 6 个枚举，SHACL 形状 S49 保护。
- 生成器：`generate_models.py` 支持多运营模型，分别生成 `backend/common/models/admin.py` 与 `frontend/src/types/admin.generated.ts`。
- 迁移：`b2c3d4e5f6a8` 建 5 张表（含自引用部门/菜单树、角色菜单唯一约束）；`alembic check` 无漂移。
- 后端：`backend/api/routers/system.py`（部门树 CRUD、角色菜单授权、菜单树 CRUD、系统参数 CRUD、登录日志查询）；登录成功/失败写入 `login_logs`。
- 种子：`backend/services/system/admin_seed.py`，由 `demo_reset` 联动；8 部门 / 29 菜单 / 107 授权 / 6 参数，mock 快照版本升到 21 同构。
- 前端：新增「角色管理 / 部门管理 / 菜单管理 / 系统参数 / 登录日志」5 个页面 + 路由菜单；用户表单部门字段改为从部门树选择。
- 验证：聚合门禁 13/13；后端 pytest 57 passed（新增 5 项系统管理回归）；浏览器逐页确认新菜单与数据渲染正常。

### 设计约定
- 角色本体来自 `UserRole` 枚举（唯一事实源），角色管理页管理其菜单授权与用户归属，不支持任意新建角色，避免与写权限策略漂移。
- 系统内置参数（is_system=true）不可删除；部门/菜单有子节点时禁止删除。


## 追加（2026-11-21 晚）：P1/P2 收尾

- 离线演示包重建：`npm run build:offline` 重新生成 `DIERP-demo.html`（含组织架构管理页），生成 `DIERP-demo-20261121-1032.zip`，更新 `DIERP-demo-说明.txt` 的数据范围。
- CI 增加 `browser-e2e` job：Postgres service + alembic + reset_demo + 后端/前端启动 + Playwright（通过 E2E_BASE_URL / CHROME_PATH 环境变量覆盖本地硬编码）。
- 报价「临时计算端点」收敛：新增规范端点 `POST /api/sd/quotations/preview-details`（试算、不写库），旧 `/calculate-details` 保留兼容；前端与 mock 同步。
- anyio 3.7.1 → 4.9.0 并显式 pin 到 requirements.txt；pytest 57 / E2E 5/5 全绿，异步运行时无回归。
- 聚合门禁构建产物移到系统临时目录，避免触发 dev 服务热重载。
- 仍待办：starlette 1.x（FastAPI 0.135.1 尚未兼容，等待框架升级）；QMS 高级特性（规划暂缓）。
