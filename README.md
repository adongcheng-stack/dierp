# ERP系统MVP版本

## 项目概述

轻量化ERP系统，验证PCB制造行业核心业务流程（销售报价→工程数据→生产执行→物料管理）

## 技术架构

- **前端**: React + TypeScript + Ant Design
- **后端**: Python + FastAPI (微服务架构)
- **数据库**: PostgreSQL
- **流程引擎**: 轻量级BPMN引擎
- **容器化**: Docker

## 项目结构

```
MVP/
├── backend/              # 后端服务
│   ├── api/             # API网关
│   ├── services/        # 微服务
│   │   ├── sd/         # 销售与分销模块
│   │   ├── eng/        # 工程管理模块
│   │   ├── pp/         # 生产计划与控制模块
│   │   └── mm/         # 物料管理模块
│   ├── common/         # 公共模块
│   │   ├── database/   # 数据库配置
│   │   ├── models/     # 数据模型
│   │   ├── utils/      # 工具函数
│   │   └── workflow/   # 流程引擎
│   └── requirements.txt
├── frontend/            # 前端应用
│   ├── src/
│   │   ├── components/ # 公共组件
│   │   ├── modules/    # 业务模块
│   │   ├── services/   # API服务
│   │   └── utils/      # 工具函数
│   └── package.json
├── docker/              # Docker配置
├── docs/                # 文档
└── 需求/                # 需求文档

```

## 核心功能模块

### 1. SD（销售与分销）模块
- 客户建档
- 报价单管理（三级审核）
- 销售订单管理
- 订单评审流程
- 发货与签收

### 2. ENG（工程管理）模块
- BOM管理
- 工艺路线管理
- MI管理
- 生产版本建立

### 3. PP（生产计划与控制）模块
- 工作中心管理
- 工序报工
- 生产订单关闭
- 生产进度看板

### 4. MM（物料管理）模块
- 物料主数据管理
- 生产领料
- 库存扣减

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- Docker (可选)

### 后端启动

**Windows用户注意：** 如果 `pip` 命令不可用，请使用 `py -m pip` 代替。

#### 方式1：使用启动脚本（推荐）

**Windows PowerShell:**
```powershell
cd backend
.\start.ps1
```

**Windows CMD:**
```cmd
cd backend
start.bat
```

#### 方式2：手动启动

```bash
cd backend

# 1. 安装依赖（首次运行）
# Windows: py -m pip install -r requirements.txt
# Linux/Mac: pip install -r requirements.txt
pip install -r requirements.txt

# 2. 配置环境变量（首次运行）
# 复制 .env.example 为 .env 并修改数据库连接信息
# Windows: copy .env.example .env
# Linux/Mac: cp .env.example .env

# 3. 创建数据库（首次运行）
# 方法A: 使用Python脚本（如果.env配置正确）
#   Windows: py create_database.py
#   Linux/Mac: python create_database.py
# 方法B: 使用psql命令行工具
#   psql -U postgres -c "CREATE DATABASE hserp_mvp;"
# 方法C: 使用pgAdmin图形界面创建数据库
#   详细说明请查看 docs/数据库设置指南.md

# 4. 初始化数据库表（首次运行）
# Windows: py init_db.py
# Linux/Mac: python init_db.py

# 4. 启动服务
# Windows PowerShell: 
#   $env:PYTHONPATH = ".."
#   py -m uvicorn api.main:app --reload
# Linux/Mac: 
#   export PYTHONPATH=..
#   uvicorn api.main:app --reload
```

**重要提示：**
- 确保PostgreSQL数据库已安装并运行
- 确保数据库 `hserp_mvp` 已创建
- 首次运行前必须执行 `init_db.py` 初始化数据库

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

前端访问地址：http://localhost:3000
后端API文档：http://localhost:8000/docs

### 默认账户
- 用户名：admin
- 密码：admin123

**注意：** 生产环境请立即修改默认密码！

## 开发计划

- [x] 项目架构搭建
- [x] 数据库模型设计
- [x] 编号生成器实现
- [x] SD模块开发
- [x] ENG模块开发
- [x] PP模块开发
- [x] MM模块开发
- [x] 流程引擎实现
- [x] 前端界面开发
- [x] 用户认证和基础权限
- [ ] 完善表单页面（创建/编辑）
- [ ] 完善审核流程
- [ ] 数据导入导出
- [ ] 生产进度看板可视化
- [ ] 测试与部署

