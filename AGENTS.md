# 牛来（niulai）项目开发与 AI 编码规范

## 一、 项目概况与核心理念

- **项目定位**：牛来（niulai）—— A 股行情分析、短线情绪监控、游资追踪与信息推送服务。
- **技术栈**：FastAPI (Python 3.12) + Vue 3 / Vite 前端 + SQLite (WAL 模式) + Docker Compose 容器化部署（服务端口 `8088`）。
- **核心理念**：
  1. **简洁至上 (KISS)**：崇尚简洁与可维护性，避免过度工程化与冗余依赖；单端口运行，零外部重型组件。
  2. **第一性原理与多源容错**：立足数据本质；主备数据源（东财/腾讯/开盘啦/同花顺）自动故障转移与优雅降级，单源异常绝不引发全页白屏。
  3. **事实为本与严禁穿透轰炸**：优先使用指数自带统计或批量打包接口，严禁单接口发起数十次 HTTP 循环请求。

---

## 二、 工作流与修改验证规范（必须严格执行）

每次代码修改完成后，必须根据修改类型执行以下闭环验证流程：

### 1. 只修改文档 / 配置说明
- 直接 `git add <file>` + `git commit`，无需重建容器。

### 2. 修改后端 Python 代码
```bash
pytest tests/                # 1. 运行单元测试
docker compose up -d --build # 2. 重建并重启容器使新代码生效
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8088/ # 3. 验证服务返回 200
```

### 3. 修改前端 Vue / JS / CSS 代码
前端在 Docker 构建阶段打包编译，故必须完成本地校验与容器重建：
```bash
(cd frontend && npm run build)  # 1. 本地构建验证前端语法与产物无误
docker compose up -d --build    # 2. 重建容器（内含前端构建 + 后端挂载）
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8088/ # 3. 验证服务返回 200
```

---

## 三、 后端代码开发规范（Python 3.12 & FastAPI）

### 1. 架构分层
- `backend/datasource/`：外部行情与数据源封装。统一使用 `FailoverClient` 承载重试、节点冷却与请求合并。
- `backend/analyzer/`：核心算法与量化计算（大盘统计、两市量能、技术指标、交易日历、选股引擎）。
- `backend/db/`：SQLite 存储与日志。必须保持**每线程独立连接**与**全局 `_lock` 写锁**；日志表必须带 **8000 条上限自动清理**机制。
- `backend/api/routes/`：REST API 路由。按业务域拆分（`market`、`stocks`、`watchlist`、`alerts`、`calendar` 等）。

### 2. 路由与接口设计
- **参数校验**：GET 查询参数必须使用 `Query(...)` 显式声明 `min_length/max_length/ge/le`；POST/PUT 请求体必须定义 Pydantic BaseModel。
- **缓存策略**：高频行情接口必须添加 `@ttl_cache(ttl=...)`（交易时段 2~5s，非交易时段 30~60s），严禁直接透传外部源。
- **平盘与真假值陷阱**：处理股票涨跌幅、涨跌额等数值字段时，**严禁使用 `or` 短路操作**（如 `p.get("change") or 0` 会把平盘 0.0 误判为 falsy），必须使用显式的 `is not None` 判断。

---

## 四、 前端代码开发规范（Vue 3 SFC & Composition API）

### 1. 组件与脚本范式
- 统一使用 `<script setup>` 组合式 API；
- 复杂逻辑必须解耦并沉淀为 `composables/`（如 `usePolling`、`useTableSort`、`usePageTab`、`useStockMeta`）。

### 2. 状态生命周期与内存管理
- **资源清理**：所有 `setInterval`、`setTimeout`、`window.addEventListener`、ECharts 实例必须在 `onUnmounted` 钩子中彻底销毁/解绑。
- **后台休眠轮询**：定时轮询必须使用 `usePolling`，切到后台标签页时自动挂起，切回前台立即刷新唤醒。
- **Tab 跨刷新保持**：页面内多 Tab（如自选/持仓、连板/原因）统一使用 `usePageTab('page_key', 'default_tab')`，同页刷新保持，跨路由离开再返回时回到默认 Tab。
- **表格排序记忆**：所有带列头排序的表格必须使用 `useTableSort(rowsRef, 'table_storage_key')` 或在 `StockTable` 中支持 `storageKey`，跨刷新保持排序列与升降序。

---

## 五、 UI / UX 视觉与交互设计规范

### 1. 金融配色语义（A 股标准）
- 严禁硬编码 Hex 颜色代码，必须使用系统全局 CSS 变量：
  - **上涨 / 强势**：`var(--up)`（深色 `#f04444` / 浅色 `#d92d20`），背景 `var(--up-bg)`。
  - **下跌 / 弱势**：`var(--down)`（深色 `#2fbf8f` / 浅色 `#0b8f63`），背景 `var(--down-bg)`。
  - **平盘 / 次要信息**：`var(--text-dim)`（`#8b9099`）。
  - **核心强调 / 主色**：`var(--accent)`（`#4c9aff` / `#2563eb`），背景 `var(--accent-bg)`。
  - **卡片与容器**：`var(--bg-card)`、`var(--border)`、`var(--kv-bg)`。

### 2. 表格与数字排版
- 价格、涨跌幅、成交额、成交量等数值列统一使用等宽数字（`font-variant-numeric: tabular-nums`）；
- 数值展示必须使用 `utils.js` 统一封装的格式化工具（`fmtPrice`、`fmtPct`、`fmtAmount`、`fmtNum`、`pctClass`）。

### 3. 交互与动效
- 加载态采用轻量骨架或 Spinner，避免全屏硬闪烁；
- 点击操作必须支持即时响应（Active 状态与 Hover 微动效）；
- 核心卡片支持一键整页/区域截图（`captureElement`）。

---

## 六、 Git 提交与安全准则

- **精准提交**：严格只 `git add <file>` 本次修改的文件，**严禁 `git add -A` / `git add .`**。
- **安全防泄露**：`.env`、`.env.*`、AI API Key、`data/`、`logs/`、`*.log` 严禁提交。
- **提交信息前缀**：遵循语义化前缀，如 `feat:`（新功能）、`fix:`（修复）、`perf:`（性能优化）、`style:`（UI样式）、`docs:`（文档）。
- **同步远端**：提交后及时 `git push` 到 origin。
