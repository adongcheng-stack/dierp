# 构建上下文：仓库根目录
# docker build -f docker/backend.Dockerfile -t dierp-backend .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY ontology ./ontology

# 安全：容器内不得使用占位默认密钥；启动时由环境变量注入。
ENV SECRET_KEY=change-me-in-production

EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
