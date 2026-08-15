# 盯盘（dingpan）

一个**自用的 A 股盘中分析 Web 工具**：浏览器打开即可一屏查看大盘概况、板块轮动、热门股与资金流向，盘中自动 3~5 秒刷新，随时查询任意个股的实时行情（分时图、五档盘口、成交明细、资金流），并支持监控提醒、持仓盈亏与 AI 分析。

- 数据来源：东方财富 / 腾讯**免费公开行情接口**（无需账号、无需付费）；K 线失败时降级 TickFlow 免费日K；压力/支撑可走百度公开接口
- 本地存储：SQLite（`data/stock.db`）保存全 A 股名称（含拼音首字母/全拼）、自选、持仓、监控、设置与运行日志
- 形态：Web 应用（FastAPI 后端 + Vue3 前端，单端口启动）
- 合规说明：仅个人学习与行情分析，不构成投资建议；数据版权归数据源所有，请勿商业分发；**勿将 `data/` 或含 AI Key 的明文备份提交到仓库**

---

## 快速启动

```bash
./start.sh
```

首次运行会自动：创建 Python 虚拟环境 → 安装依赖 → 构建前端 → 启动服务。

启动后浏览器访问：**http://127.0.0.1:8088**

> 手动方式：
> ```bash
> python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
> (cd frontend && node_modules/.bin/vite build)   # 推荐直调 vite，避免管道卡死
> .venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8088
> ```

---

## 功能总览

| 页面 | 功能 |
|---|---|
| **盘面总览** | 上证/深成/创业板/科创50/沪深300 指数行情；两市成交额、涨跌家数、涨停家数等情绪指标；行业/概念板块涨幅 TOP；涨速榜预览；全球指数 |
| **板块分析** | 行业/概念板块排行（按涨幅/主力净流入/成交额排序）；点击板块展开成分股列表 |
| **板块异动** | 5 分钟板块涨速拉升/跳水榜（约 5s 轮询） |
| **热门与资金** | 涨速榜、个股主力净流入榜、热门股多维度榜、涨停池、连板梯队、板块资金流榜、同花顺热榜 |
| **个股实时** | 搜索（代码/名称/拼音首字母/全拼）→ 快照、分时/K线、五档、成交明细、资金流、龙虎榜、新闻公告、百度压力支撑、数据源标签 |
| **自选 / 持仓** | 自选与持仓 Tab 分离；持仓盈亏与收益快照；录入持仓自动加自选 |
| **价格监控** | 价格 / 点数 / 涨跌幅 / **涨速** 阈值 + 浏览器桌面通知 |
| **AI 分析** | 设置页配置 API Key（仅本地）；个股页流式分析（兼容 reasoning） |
| **设置** | 主题、刷新间隔、分时/K线坐标、自选导入导出、股票列表同步、接口/行为/数据源日志 |

**轮询策略**：总览/板块 5 秒，板块异动 5 秒，榜单/个股快照 3 秒，个股明细/资金流 10 秒；非交易时段自动降频。

---

## 目录结构

```
dingpan/
├── backend/
│   ├── app.py                # FastAPI 入口（日志中间件 / SPA / SQLite 启动）
│   ├── config.py             # 节点列表、缓存、交易时段、节假日配置
│   ├── db/                   # SQLite：股票列表 / 自选 / 持仓 / 监控 / 设置 / 日志
│   ├── datasource/
│   │   ├── eastmoney.py      # 东财客户端：节点健康 + 请求合并 + 故障转移
│   │   ├── tencent.py        # 腾讯客户端：五档盘口/内外盘/分时降级
│   │   └── models.py         # 统一数据模型（Pydantic）
│   ├── analyzer/
│   │   ├── market.py         # 大盘概况聚合
│   │   ├── sector.py         # 板块排行/详情
│   │   ├── rank.py           # 涨速/资金流/热门榜单
│   │   └── schedule.py       # 交易时段与节假日判断
│   └── api/routes/           # REST 按域拆分：market/stocks/watchlist/alerts/ai/meta
├── data/stock.db             # 运行时生成（不入库）
├── frontend/                 # Vue3 + Vite + ECharts（个股页拆为 stock/* 子组件）
├── scripts/verify.py         # 数据链路 CLI 验证脚本
├── tests/                    # 单元（mock）+ 端到端
├── PERFORMANCE.md            # 性能与数据源说明
├── start.sh                  # 一键启动
└── requirements.txt
```

---

## 接口一览（REST）

| 接口 | 说明 |
|---|---|
| `GET /api/market/overview` | 大盘概况（指数/成交额/涨跌家数/涨停数） |
| `GET /api/sectors?type=industry\|concept&sort=...` | 板块排行 |
| `GET /api/sectors/{code}` | 板块详情（成分股） |
| `GET /api/sectors/moneyflow` | 板块主力净流入榜 |
| `GET /api/sector-moves` | 板块异动（涨速） |
| `GET /api/rank/hot?by=...` | 热门股榜（涨幅/成交额/换手/量比/涨速） |
| `GET /api/rank/zhangsu` | 涨速榜 |
| `GET /api/rank/moneyflow` | 个股主力净流入榜 |
| `GET /api/stocks/{code}` | 个股实时详情（含五档盘口、`data_source`） |
| `GET /api/stocks/{code}/trends` | 分时数据 |
| `GET /api/stocks/{code}/kline` | K 线 + 指标 |
| `GET /api/stocks/{code}/baidu-sr` | 百度压力/支撑 |
| `GET /api/stocks/{code}/ticks` | 成交明细 |
| `GET /api/stocks/{code}/moneyflow` | 近 N 日主力资金流 |
| `GET /api/stocks/batch?codes=...` | 批量快照（自选股） |
| `GET /api/search?q=` | 股票搜索（SQLite 优先，支持全拼） |
| `GET /api/market/limit-up` | 涨停池 / 连板梯队数据 |
| `GET/POST/DELETE /api/watchlist` | 自选股 |
| `GET/PUT/DELETE /api/positions*` | 持仓与盈亏摘要 |
| `GET/POST/PUT/DELETE /api/alerts*` | 价格/涨跌幅/涨速监控 |
| `POST /api/ai/chat` | AI 流式代理（Key 存本地设置） |
| `GET /api/settings` | 用户设置 |
| `GET /api/logs/api` | 接口耗时日志 |
| `GET /api/trading/time` | 交易时段状态 |

交互式接口文档：启动后访问 `http://127.0.0.1:8088/docs`

---

## 测试与验证

```bash
# 默认 mock 外部行情，不连东财（CI 友好）
.venv/bin/python -m pytest tests/ -q

# 可选：CLI 验证真实数据链路
.venv/bin/python scripts/verify.py --stock 600519
```

---

## 数据源与容错设计

| 数据 | 主源 | 备源/容错 |
|---|---|---|
| 指数/板块/榜单/明细 | 东方财富 push2 节点群 | 节点健康冷却 + 请求合并 + push2delay；非交易时段缩短超时、延长缓存 |
| 分时 | 东方财富 push2his | 失败自动降级腾讯（可推导均价线） |
| 个股详情/五档盘口 | 东方财富快照 + 腾讯盘口 | 东财/腾讯并发；响应带 `data_source`（东财/腾讯/东财+腾讯） |
| 涨停池 / 连板 | 东方财富 push2ex | 自动定位最近交易日 |
| 搜索 | 本地 SQLite（首字母+全拼） | 未命中再降级东财 searchapi |
| K 线 | 东方财富 push2his | 腾讯 → TickFlow；百度补齐额/涨跌 |
| 资金流历史 | 东方财富 push2his | 空数据容错 + 前端「暂不可用」标签 |
| 压力/支撑 | 百度公开接口 | 失败回退本地 analysis-data |

免费接口偶有风控/抖动，以上容错保证页面不崩；接口全部不可用时返回 503 并提示。

## 已知说明

- **北向资金不做**：交易所已停止盘中披露北向资金，公开接口无实时值。
- **跌停池**：东财对应接口曾 404，情绪指标偏涨停侧。
- **日经/韩综分时**：腾讯不支持，依赖东财历史节点是否被风控。
- **同花顺热榜解读**：上游仅对部分标的提供 `analyse`，无正文时降级展示标题/概念。
- **节假日配置**：`backend/config.py` 的 `TRADING_HOLIDAYS` 预置主要节假日，可按交易所公告增删。
- **自选跨端口**：自选/设置存 SQLite；首次打开可迁移 localStorage。
- 前端构建：优先 `frontend/node_modules/.bin/vite build`；产物在 `frontend/dist`。
