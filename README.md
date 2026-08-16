<p align="center">
  <img src="frontend/public/niulai.png" width="128" alt="牛来 niulai logo">
</p>

<h1 align="center">牛来 niulai</h1>

<p align="center">
  <b>A 股盘中实时行情分析 Web 工具</b><br>
  浏览器打开即用的一屏式 A 股行情分析平台：大盘概况、板块轮动、热门股与资金流向实时刷新，支持个股深度行情、自选持仓管理、价格监控与 AI 智能分析。
</p>

<p align="center">
  <b>免费数据源 · 本地存储 · 单端口部署 · 零成本上手</b>
</p>

数据全部来自东方财富 / 腾讯等**免费公开行情接口**（无需账号、无需付费），业务数据存本地 SQLite，无需任何外部数据库。个人自用或作为学习 A 股行情数据接口的最佳实践参考。

---

## 核心特性

- **一屏看盘**：指数、情绪指标、板块涨幅 TOP、涨速榜、全球指数，盘中 3~5 秒自动刷新
- **板块轮动**：行业 / 概念板块排行（涨幅 / 主力净流入 / 成交额），板块异动 5 分钟涨速拉升 / 跳水榜
- **热门与资金**：涨速榜、主力净流入、热门股多维度榜、涨停池、连板梯队、同花顺热榜
- **个股深度行情**：搜索（代码 / 名称 / 拼音首字母 / 全拼）→ 分时图、K 线、五档盘口、成交明细、资金流、龙虎榜、新闻公告、筹码分布、百度压力 / 支撑
- **自选与持仓**：独立 Tab 管理，持仓盈亏与收益快照，录入持仓自动加自选
- **价格监控**：价格 / 点数 / 涨跌幅 / 涨速阈值触发，浏览器桌面通知 + 飞书推送；持仓异动监控（大笔买卖、急速拉升跳水）
- **盘后选股**：全 A 日 K 增量同步到本地，突破 / 金叉 / 放量三规则扫描，结果可推飞书
- **AI 分析**：本地配置 API Key，聚合快照 / 分时 / K 线 / 资金流 / 压力支撑后流式分析（兼容 reasoning 输出）
- **强容错**：东财 / 腾讯多数据源并发取数 + 故障转移 + 节点健康管理，免费接口抖动不影响页面

---

## 快速开始

### 一键启动

```bash
./start.sh
```

首次运行会自动：创建 Python 虚拟环境 → 安装依赖 → 构建前端 → 启动服务。

启动后浏览器访问：**http://127.0.0.1:8088**

### 手动启动

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2. 构建前端
(cd frontend && node_modules/.bin/vite build)

# 3. 启动服务
.venv/bin/uvicorn backend.app:app --host 0.0.0.0 --port 8088
```

### 环境要求

- Python 3.10+
- Node.js 18+（仅构建前端需要）

---

## 界面功能

| 页面 | 功能 |
|---|---|
| **盘面总览** | 上证/深成/创业板/科创50/沪深300 指数行情；两市成交额、涨跌家数、涨停家数等情绪指标；行业/概念板块涨幅 TOP；涨速榜预览；全球指数 |
| **板块分析** | 行业/概念板块排行（按涨幅/主力净流入/成交额排序）；点击板块展开成分股列表 |
| **板块异动** | 5 分钟板块涨速拉升/跳水榜（约 5s 轮询） |
| **热门与资金** | 涨速榜、个股主力净流入榜、热门股多维度榜、涨停池、连板梯队、板块资金流榜、同花顺热榜 |
| **个股实时** | 搜索（代码/名称/拼音首字母/全拼）→ 快照、分时/K线、五档、成交明细、资金流、龙虎榜（席位标签/上榜次数）、新闻公告、百度压力支撑、筹码分布、数据源标签 |
| **自选 / 持仓** | 自选与持仓 Tab 分离；持仓盈亏与收益快照；录入持仓自动加自选 |
| **价格监控** | 价格 / 点数 / 涨跌幅 / 涨速阈值 + 浏览器桌面通知；持仓异动监控（大笔买卖/急速拉升跳水等，桌面 + 飞书提醒） |
| **飞书通知** | 监控告警 / 持仓异动 / 盘后选股结果推送飞书自定义机器人卡片；设置页测试推送 |
| **盘后选股** | 全 A 日 K 增量同步到 SQLite；突破 / 金叉 / 放量三规则扫描，结果可推飞书 |
| **AI 分析** | 设置页配置 API Key（仅本地）；个股页流式分析（兼容 reasoning）；聚合快照/分时/K线/资金流/压力支撑后分析 |
| **设置** | 主题、刷新间隔、分时/K线坐标、自选导入导出、股票列表/概念同步、接口/行为/数据源日志、飞书 Webhook |

**轮询策略**：总览/板块 5 秒，板块异动 5 秒，榜单/个股快照 3 秒，个股明细/资金流 10 秒，监控/持仓异动检查 8 秒；非交易时段自动降频。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3 · FastAPI · Pydantic · SQLite |
| 前端 | Vue 3 · Vite · ECharts |
| 测试 | pytest（mock 数据源，CI 友好） |
| 数据源 | 东方财富、腾讯、新浪、百度、同花顺（免费公开接口） |

---

## 目录结构

```
niulai/
├── backend/
│   ├── app.py                # FastAPI 入口（日志中间件 / SPA / SQLite 启动）
│   ├── config.py             # 节点列表、缓存、交易时段、节假日配置
│   ├── db/                   # SQLite：股票列表 / 自选 / 持仓 / 监控 / 设置 / 日志
│   │   ├── store.py          # 建表与各领域读写
│   │   ├── sync.py           # 全 A 名称/行业/概念标签后台同步
│   │   ├── daily_sync.py     # 全 A 日 K 增量同步（盘后选股数据源）
│   │   ├── lhb_seats.py      # 龙虎榜游资/机构席位标签库
│   │   ├── pinyin.py         # 拼音首字母 / 全拼
│   │   └── tags.py           # 板块/ST/北交徽标推断
│   ├── datasource/
│   │   ├── eastmoney.py      # 东财客户端：节点健康 + 请求合并 + 故障转移
│   │   ├── tencent.py        # 腾讯客户端：五档盘口/内外盘/分时/K线降级
│   │   ├── lhb.py            # 龙虎榜（上榜次数/席位分类/历史）
│   │   ├── ths.py            # 同花顺热榜
│   │   └── models.py         # 统一数据模型（Pydantic）
│   ├── analyzer/
│   │   ├── market.py         # 大盘概况聚合 / 量能
│   │   ├── sector.py         # 板块排行/详情
│   │   ├── rank.py           # 涨速/资金流/热门榜单
│   │   ├── screener.py       # 盘后选股引擎（突破/金叉/放量）
│   │   ├── indicators.py     # MA/MACD/KDJ/RSI/BOLL
│   │   └── schedule.py       # 交易时段与节假日判断
│   ├── notify/feishu.py      # 飞书自定义机器人推送
│   └── api/routes/           # REST 按域拆分：market/stocks/watchlist/alerts/ai/meta/screener
├── data/stock.db             # 运行时生成（不入库）
├── frontend/                 # Vue3 + Vite + ECharts（个股页拆为 stock/* 子组件）
├── scripts/verify.py         # 数据链路 CLI 验证脚本
├── tests/                    # 单元（mock）+ 端到端
├── PERFORMANCE.md            # 性能与数据源说明
├── 开发进度.md                # 迭代开发记录（倒序）
├── start.sh                  # 一键启动
└── requirements.txt
```

---

## API 一览（REST）

启动后访问 **http://127.0.0.1:8088/docs** 查看交互式接口文档（Swagger）。

**大盘与指数**

| 接口 | 说明 |
|---|---|
| `GET /api/market/overview` | 大盘概况（指数/成交额/涨跌家数/涨停数） |
| `GET /api/market/volume` | 两市量能（放量/缩量，30s 缓存） |
| `GET /api/market/moneyflow` | 大盘资金流向（东财 dpzjlx） |
| `GET /api/market/limit-up` | 涨停池 |
| `GET /api/market/limit-break` | 炸板池 |
| `GET /api/market/stock-changes` | 盘中个股异动（大笔买卖/急速拉升跳水） |
| `GET /api/market/lhb` | 东财龙虎榜（最近交易日） |
| `GET /api/global/indices` | 全球指数（日韩/亚太/美股） |
| `GET /api/global/{secid}/trends` | 全球指数分时 |
| `GET /api/global/{secid}/kline` | 全球指数 K 线 |
| `GET /api/indices/quote` | 单指数快照 |
| `GET /api/indices/quotes` | 批量指数快照（导航栏） |

**板块与榜单**

| 接口 | 说明 |
|---|---|
| `GET /api/sectors?type=industry\|concept&sort=...` | 板块排行 |
| `GET /api/sectors/{code}` | 板块详情（成分股） |
| `GET /api/sectors/moneyflow` | 板块主力净流入榜 |
| `GET /api/sectors/{code}/moneyflow-history` | 板块资金流历史 |
| `GET /api/sector-moves` | 板块异动（涨速） |
| `GET /api/etf/rank` | ETF 涨跌排行 |
| `GET /api/rank/hot?by=...` | 热门股榜（涨幅/成交额/换手/量比/涨速） |
| `GET /api/rank/zhangsu` | 涨速榜 |
| `GET /api/rank/moneyflow` | 个股主力净流入榜 |
| `GET /api/ths/hot` | 同花顺热榜 |

**个股**

| 接口 | 说明 |
|---|---|
| `GET /api/stocks/{code}` | 个股实时详情（含五档盘口、`data_source`） |
| `GET /api/stocks/{code}/trends` | 分时数据 |
| `GET /api/stocks/{code}/kline` | K 线 + 指标（百度补额/涨跌） |
| `GET /api/stocks/{code}/ticks` | 成交明细 |
| `GET /api/stocks/{code}/moneyflow` | 近 N 日主力资金流 |
| `GET /api/stocks/{code}/lhb` | 个股龙虎榜（席位标签/上榜次数/历史） |
| `GET /api/stocks/{code}/news` | 个股新闻 |
| `GET /api/stocks/{code}/announcements` | 个股公告 |
| `GET /api/stocks/{code}/baidu-sr` | 百度压力/支撑 |
| `GET /api/stocks/{code}/chip` | 筹码分布（成本分布模型） |
| `GET /api/stocks/{code}/analysis-data` | AI 分析全维度聚合数据 |
| `GET /api/stocks/batch?codes=...` | 批量快照（自选股） |
| `GET /api/search?q=` | 股票搜索（SQLite 优先，支持全拼） |

**自选 / 持仓 / 监控**

| 接口 | 说明 |
|---|---|
| `GET/POST/DELETE /api/watchlist` | 自选股 |
| `GET/PUT/DELETE /api/positions*` | 持仓与盈亏摘要 / 收益快照 / 流水 |
| `GET/POST/PUT/DELETE /api/alerts*` | 价格/涨跌幅/涨速监控 |
| `GET /api/alerts/check` | 监控触发检查（前端轮询） |
| `GET /api/alerts/check-changes` | 持仓异动检查（前端轮询 + 飞书推送） |

**AI 与选股**

| 接口 | 说明 |
|---|---|
| `POST /api/ai/chat` | AI 流式代理（Key 存本地设置） |
| `POST /api/screener/sync-bars` | 触发全 A 日 K 后台同步 |
| `GET /api/screener/sync-status` | 日 K 同步进度 |
| `POST /api/screener/run` | 执行选股扫描 |
| `GET /api/screener/rules` | 选股规则列表 |
| `GET /api/screener/runs` | 历史选股任务 |
| `GET /api/screener/runs/{id}` | 选股任务详情 |

**元数据与系统**

| 接口 | 说明 |
|---|---|
| `GET /api/meta/stocks` | 股票列表同步状态 |
| `POST /api/meta/stocks/sync` | 手动同步全 A + ETF 列表 |
| `POST /api/meta/tags/sync` | 后台同步概念标签 |
| `GET /api/meta/tags/sync/status` | 标签同步进度 |
| `GET /api/meta/lookup/{code}` | 本地股票元信息（名称/行业/概念秒出） |
| `GET /api/logs/api` | 接口耗时日志 |
| `GET /api/logs/actions` | 页面操作日志 |
| `GET /api/logs/datasource` | 数据源日志 |
| `POST /api/log/action` | 前端行为日志上报 |
| `GET /api/crawl-article` | 代理抓取新闻/公告正文 |
| `GET /api/trading/time` | 交易时段状态 |
| `GET /api/health` | 健康检查 |
| `GET/POST /api/settings` | 用户设置 |
| `POST /api/notify/feishu/test` | 飞书推送测试 |
| `GET /api/lhb/seats` | 龙虎榜席位标签库 |
| `POST /api/lhb/seats/sync` | 重置/同步席位标签库 |

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
| 涨停池 / 炸板池 / 盘中异动 | 东方财富 push2ex | 自动定位最近交易日 |
| 龙虎榜 / 资金流明细 | 东方财富 datacenter-web | 空数据容错 + 前端「暂不可用」标签 |
| 搜索 | 本地 SQLite（首字母+全拼） | 未命中再降级东财 searchapi |
| K 线 | 东方财富 push2his | 腾讯 → 新浪（指数）→ TickFlow；百度补齐额/涨跌 |
| 资金流历史 | 东方财富 push2his | 空数据容错 + datacenter 兜底 + 前端「暂不可用」标签 |
| 压力/支撑 | 百度公开接口 | 失败回退本地 analysis-data |
| 热榜 | 同花顺 | 部分标的无 `analyse` 正文时降级标题/概念 |
| 新闻 / 公告 | 东方财富搜索 / 资讯流 | 公告正文走 np-cnotice 内容 API；全文经后端代理抓取 |
| 日 K 同步（选股） | 东财 kline（复用上面的降级链） | 增量写入 SQLite `daily_bars` |
| 通知 | 浏览器桌面通知 | 飞书自定义机器人卡片（可选） |

免费接口偶有风控/抖动，以上容错保证页面不崩；接口全部不可用时返回 503 并提示。

---

## 已知限制

- **北向资金**：交易所已停止盘中披露北向资金，公开接口无实时值。
- **跌停池**：东财对应接口曾 404，情绪指标偏涨停侧。
- **日经/韩综分时**：腾讯不支持，依赖东财历史节点是否被风控。
- **选股日 K 同步**：首次全 A 同步较慢（约 50~80 分钟，受免费接口限速），增量很快；`daily_bars` 的 `amount` 在腾讯降级时可能缺失，突破规则依赖成交额，可能漏命中。
- **节假日配置**：`backend/config.py` 的 `TRADING_HOLIDAYS` 预置主要节假日，可按交易所公告增删。

---

## 免责声明

本项目仅供个人学习与行情分析使用，**不构成任何投资建议**。股市有风险，入市需谨慎。

数据版权归各数据源所有，请勿商业分发。**请勿将 `data/` 目录或含 AI Key 的明文备份提交到仓库**（`.gitignore` 已默认忽略）。

---

## License

[MIT](LICENSE)
