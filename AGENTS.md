# 工作规则（必须遵守）

## 项目简介

牛来（niulai）：A 股行情分析与信息推送服务。FastAPI（Python 3.12）+ Vue3/Vite 前端，服务端口 `8088`，Docker Compose 部署。

## 修改流程（按修改类型分流）

### 1. 只改文档/注释/配置说明

直接 `git add` + commit，无需验证与重建容器。

### 2. 改后端代码

```bash
pytest tests/                # 1. 运行测试
docker compose up -d --build # 2. 重建并重启容器使新代码生效
curl http://127.0.0.1:8088/  # 3. 验证服务返回 200
```

### 3. 改前端代码

前端在 Docker 内重新构建，故必须重建容器验证构建产物生效：

```bash
(cd frontend && npm run build)  # 1. 本地构建验证前端无误
docker compose up -d --build    # 2. 重建容器（内含前端构建 + 后端）
curl http://127.0.0.1:8088/     # 3. 验证服务返回 200
```

## Git 提交规范

- **提交范围**：只 `git add` 本次涉及的文件，**禁止 `git add -A` / `git add .`**，避免误加日志、数据等目录。
- **禁止提交密钥**：`.env`、`.env.*`、AI Key、`data/`、`logs/`、`*.log` 一律不得提交（已在 .gitignore 中忽略，提交前仍需自查）。
- **提交信息风格**：遵循仓库现有约定，使用前缀，如 `feat:`、`fix:`、`style:`、`docs:`、`revert:`。
- 提交后 `git push` 到 origin。
