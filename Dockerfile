# ---- 阶段 1：构建前端 ----
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 阶段 2：运行时 ----
FROM python:3.12-slim
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY --from=frontend-build /app/dist frontend/dist
EXPOSE 8088
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8088"]
