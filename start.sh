#!/usr/bin/env bash
# 牛来 (niulai) - 一键启动脚本
set -e
cd "$(dirname "$0")"

# 1. Python 环境
if [ ! -d .venv ]; then
  echo "[1/3] 创建 Python 虚拟环境并安装依赖..."
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt
else
  echo "[1/3] 使用现有虚拟环境 .venv"
fi

# 2. 前端构建（dist 不存在时）
if [ ! -d frontend/dist ]; then
  echo "[2/3] 构建前端..."
  (cd frontend && npm install --no-audit --no-fund && npm run build)
else
  echo "[2/3] 使用现有前端构建 frontend/dist"
fi

# 3. 启动服务
echo "[3/3] 启动服务: http://127.0.0.1:8088"
exec .venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8088
