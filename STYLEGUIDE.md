# 牛来（niulai）代码风格与 UI 设计系统规范指南

本指南定义了「牛来」项目的代码架构、编码范式、UI 视觉规范与设计系统最佳实践，供所有开发者和 AI 编程工具共同遵守。

---

## 目录
1. [技术架构总览](#1-技术架构总览)
2. [后端代码规范 (Python / FastAPI)](#2-后端代码规范)
3. [前端代码规范 (Vue 3 / Vite)](#3-前端代码规范)
4. [UI / UX 视觉设计系统](#4-ui--ux-视觉设计系统)
5. [数据源与缓存策略](#5-数据源与缓存策略)
6. [质量保障与发布工作流](#6-质量保障与发布工作流)

---

## 1. 技术架构总览

- **原则**：**KISS（Keep It Simple, Stupid）**，崇尚极简与高内聚，零多余抽象。
- **服务形态**：单服务端口 `8088`，内置静态资源托管，Docker Compose 一键容器化部署。
- **存储机制**：嵌入式 SQLite，采用 WAL 日志并发读写，全局线程锁保护。

---

## 2. 后端代码规范 (Python / FastAPI)

### 2.1 目录职责
```
backend/
├── datasource/      # 外部数据源通信层（东财、腾讯、开盘啦、同花顺）
├── analyzer/        # 核心算法与业务计算（大盘聚合、技术指标、日历推算、选股器）
├── db/              # SQLite 存储、标签、自选、游资、历史快照与日志
└── api/routes/      # 外部 REST API 接口（按域拆分）
```

### 2.2 编码规范
1. **显式类型与校验**：
   - 所有的 API 入参必须使用 `Query(..., ge=..., le=...)` 或 Pydantic `BaseModel` 进行严格类型校验。
2. **平盘与数值安全性**：
   - 股票行情中涨跌额/涨跌幅为 `0.0`（平盘）是常见合法数值，**严禁使用 `p.get("change") or 0`**，必须使用：
     ```python
     val = p.get("change")
     change = float(val) if val is not None else 0.0
     ```
3. **缓存与穿透防护**：
   - 高频数据接口必须使用 `@ttl_cache(ttl=...)` 装饰器，禁止无节制穿透外部服务器。
4. **日志安全与控容**：
   - 所有数据库日志表写入必须遵循 8000 条上限淘汰规则，防止数据库文件无限制增长。

---

## 3. 前端代码规范 (Vue 3 / Vite)

### 3.1 架构与组件范式
1. **单文件组件**：必须采用 `<script setup>` 组合式 API。
2. **逻辑抽象为 Composables**：
   - 轮询：`usePolling.js`（内置后台标签页自动休眠与唤醒刷新）；
   - 排序记忆：`useTableSort.js`（基于 localStorage 跨刷新持久化）；
   - Tab 记忆：`usePageTab.js`（基于 sessionStorage 实现同页刷新保持，跨路由离开重置）；
   - 个股弹窗/跳转：`useStockMeta.js`；
   - 截图导出：`useScreenshot.js`。

### 3.2 内存与事件销毁
- 所有的 `setInterval`、`setTimeout`、`window.addEventListener`、ECharts 实例必须在 `onUnmounted` 阶段销毁解绑：
  ```javascript
  onMounted(() => {
    timer = setInterval(load, 5000)
  })
  onUnmounted(() => {
    clearInterval(timer)
    chartInstance?.dispose()
  })
  ```

---

## 4. UI / UX 视觉设计系统

### 4.1 全局色彩语义变量
**严禁硬编码 Hex 颜色代码**，一律使用 CSS 变量保证深色/浅色主题自适应：

| 语义变量 | 深色模式 (`dark`) | 浅色模式 (`light`) | 适用场景 |
|---|---|---|---|
| `--bg` | `#0b0c0f` | `#f6f7f8` | 全局页面主背景 |
| `--bg-card` | `#141519` | `#ffffff` | 卡片与弹窗容器背景 |
| `--bg-hover` | `#1d1f25` | `#eceef0` | 悬停态与列表激活底色 |
| `--border` | `#272a31` | `#e3e6ea` | 分割线与卡片边框 |
| `--text` | `#e6e8eb` | `#1b1f23` | 正文与主要标题 |
| `--text-dim` | `#8b9099` | `#6b7480` | 次要文字、标签、平盘 |
| `--up` | `#f04444` | `#d92d20` | **A 股上涨 / 强势 / 买入** |
| `--up-bg` | `rgba(240,68,68,0.12)` | `rgba(217,45,32,0.08)` | 上涨背景高亮 |
| `--down` | `#2fbf8f` | `#0b8f63` | **A 股下跌 / 弱势 / 卖出** |
| `--down-bg` | `rgba(47,191,143,0.12)` | `rgba(11,143,99,0.08)` | 下跌背景高亮 |
| `--accent` | `#4c9aff` | `#2563eb` | **主品牌色 / 链接 / 选中** |
| `--accent-bg` | `rgba(76,154,255,0.12)` | `rgba(37,99,235,0.08)` | 激活项浅色背景 |

### 4.2 表格与排版规范
1. **等宽数字**：所有表格中的价格、涨跌幅、成交额、成交量统一应用 `font-variant-numeric: tabular-nums`，防止数字跳动错位。
2. **统一格式化**：
   - 价格：`fmtPrice(val)`；
   - 涨跌幅：`fmtPct(val)`（自动带 `+` 号与 `%`）；
   - 成交额：`fmtAmount(val)`（自动根据单位转为“亿”或“万”）；
   - 涨跌颜色 Class：`pctClass(val)`（输出 `up`、`down`、`flat`）。

---

## 5. 数据源与缓存策略

1. **多源容错 (Failover)**：主数据源不可用时，系统自动切换至备用源或返回缓存降级数据，杜绝阻断页面渲染。
2. **批量并发**：个股多代码拉取必须使用 `stocks/batch` 分批合并，避免前端并发发起上百个单一 HTTP 请求。

---

## 6. 质量保障与发布工作流

1. **改动后端**：运行 `pytest tests/` -> 重建 `docker compose up -d --build` -> 验证 `curl http://127.0.0.1:8088/` 返回 200。
2. **改动前端**：运行 `(cd frontend && npm run build)` -> 重建 `docker compose up -d --build` -> 验证服务返回 200。
3. **Git 提交准则**：
   - 严禁 `git add -A` 或 `git add .`；
   - 严禁提交密钥、`.env`、日志与数据目录；
   - 提交信息采用语义前缀：`feat:`、`fix:`、`perf:`、`style:`、`docs:`。
