@echo off
REM 航盛电路ERP系统 - 后端启动脚本

echo 正在启动后端服务...
echo.

REM 设置PYTHONPATH为项目根目录
set PYTHONPATH=%~dp0\..

REM 检查.env文件是否存在
if not exist .env (
    echo 警告: .env文件不存在，将使用默认配置
    echo 请确保PostgreSQL数据库已创建并运行
    echo.
)

REM 启动服务
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

pause

