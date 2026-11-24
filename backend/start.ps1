# 航盛电路ERP系统 - 后端启动脚本 (PowerShell)

Write-Host "正在启动后端服务..." -ForegroundColor Green
Write-Host ""

# 设置PYTHONPATH为项目根目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
$env:PYTHONPATH = $projectRoot

Write-Host "PYTHONPATH设置为: $env:PYTHONPATH" -ForegroundColor Yellow
Write-Host ""

# 检查.env文件是否存在
if (-not (Test-Path ".env")) {
    Write-Host "警告: .env文件不存在" -ForegroundColor Yellow
    Write-Host "请确保PostgreSQL数据库已创建并运行" -ForegroundColor Yellow
    Write-Host ""
}

# 切换到backend目录
Set-Location $scriptPath

# 启动服务
Write-Host "启动后端服务在 http://localhost:8000" -ForegroundColor Green
Write-Host "API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
