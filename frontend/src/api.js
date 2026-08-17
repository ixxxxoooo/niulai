// 后端 API 封装
// @author ygw
const BASE = '/api'

async function get(path, retries = 2) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(BASE + path, { cache: 'no-store' })
      if (!r.ok) {
        let detail = `HTTP ${r.status}`
        try { detail = (await r.json()).detail || detail } catch (e) { /* ignore */ }
        if (r.status >= 500 && attempt < retries) {
          await new Promise(ok => setTimeout(ok, 300 * (attempt + 1)))
          continue
        }
        throw new Error(detail)
      }
      return r.json()
    } catch (e) {
      if (attempt < retries && (e.name === 'TypeError' || e.message.includes('fetch'))) {
        await new Promise(ok => setTimeout(ok, 300 * (attempt + 1)))
        continue
      }
      throw e
    }
  }
}

async function send(method, path, body) {
  const r = await fetch(BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  })
  if (!r.ok) {
    let detail = `HTTP ${r.status}`
    try { detail = (await r.json()).detail || detail } catch (e) { /* ignore */ }
    throw new Error(detail)
  }
  return r.json()
}

export const api = {
  overview: () => get('/market/overview'),
  marketVolume: () => get('/market/volume'),
  indicesTrends: () => get('/market/indices-trends'),

  // 开盘啦（抓包接口，容错降级）
  kaipanlaLimitUpSectors: (date = '') => get(`/kaipanla/limit-up-sectors?date=${date}`),
  kaipanlaSectorStrengths: (date = '') => get(`/kaipanla/sector-strengths?date=${date}`),
  kaipanlaSectorStrength: (code) => get(`/kaipanla/sector-strength?code=${encodeURIComponent(code)}`),
  kaipanlaSectorIntraday: (code) => get(`/kaipanla/sector-intraday?code=${encodeURIComponent(code)}`),
  kaipanlaSectorCodes: () => get('/kaipanla/sector-codes'),
  sectors: (type = 'industry', sort = 'change_pct', limit = 100) =>
    get(`/sectors?type=${type}&sort=${sort}&limit=${limit}`),
  sectorDetail: (code, limit = 100, sort = 'change_pct') =>
    get(`/sectors/${code}?sort=${sort}&limit=${limit}`),
  hot: (by = 'change_pct', limit = 50) => get(`/rank/hot?by=${by}&limit=${limit}`),
  zhangsu: (limit = 50) => get(`/rank/zhangsu?limit=${limit}`),
  moneyflow: (limit = 50) => get(`/rank/moneyflow?limit=${limit}`),
  etfRank: (by = 'change_pct', limit = 50) => get(`/etf/rank?by=${by}&limit=${limit}`),
  sectorMoneyflow: (type = 'industry', limit = 100) =>
    get(`/sectors/moneyflow?type=${type}&limit=${limit}`),
  sectorsRangeStats: (days = 5) => get(`/sectors/range-stats?days=${days}`),
  sectorConceptCode: (name, type = 'concept') => get(`/sectors/concept-code?name=${encodeURIComponent(name)}&type=${type}`),
  stock: (code) => get(`/stocks/${code}`),
  trends: (code) => get(`/stocks/${code}/trends`),
  kline: (code, period = 'day', limit = 120) => get(`/stocks/${code}/kline?period=${period}&limit=${limit}`),
  ticks: (code, limit = 100) => get(`/stocks/${code}/ticks?limit=${limit}`),
  moneyflowHistory: (code, days = 5) => get(`/stocks/${code}/moneyflow?days=${days}`),
  stockLhb: (code) => get(`/stocks/${code}/lhb`),
  batch: (codes) => get(`/stocks/batch?codes=${codes.join(',')}`),
  holdings: (code) => get(`/stocks/${code}/holdings`),
  limitUp: (limit = 100) => get(`/market/limit-up?limit=${limit}`),
  limitBreak: (limit = 100) => get(`/market/limit-break?limit=${limit}`),
  limitDown: (limit = 100) => get(`/market/limit-down?limit=${limit}`),
  stockLimitTag: (code) => get(`/stocks/${code}/limit-tag`),
  thsHot: (type = 'hour', limit = 50) => get(`/ths/hot?type=${type}&limit=${limit}`),
  lhb: (limit = 50, date = '') => get(`/market/lhb?limit=${limit}${date ? `&date=${date}` : ''}`),
  indexQuote: (secid) => get(`/indices/quote?secid=${encodeURIComponent(secid)}`),
  indicesQuotes: (secids = '1.000001,0.399006,1.000688') =>
    get(`/indices/quotes?secids=${encodeURIComponent(secids)}`),
  marketMoneyflow: (days = 5) => get(`/market/moneyflow?days=${days}`),
  quoteTrends: (secid) => get(`/quotes/trends?secid=${encodeURIComponent(secid)}`),
  quoteKline: (secid, period = 'day', limit = 120) =>
    get(`/quotes/kline?secid=${encodeURIComponent(secid)}&period=${period}&limit=${limit}`),
  tradingTime: () => get('/trading/time'),
  search: (q, limit = 10) => get(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  globalIndices: () => get('/global/indices'),
  globalSectors: (region = '') => get(`/global/sectors${region ? `?region=${region}` : ''}`),
  globalTrends: (secid) => get(`/global/${secid}/trends`),
  globalKline: (secid, period = 'day', limit = 120) => get(`/global/${secid}/kline?period=${period}&limit=${limit}`),
  sectorMoves: (dir = 'up', limit = 30) => get(`/sector-moves?dir=${dir}&limit=${limit}`),
  sectorMoneyflowHistory: (code, days = 5) => get(`/sectors/${code}/moneyflow-history?days=${days}`),

  // SQLite：自选 / 设置 / 日志
  watchlist: () => get('/watchlist'),
  watchlistAdd: (code) => send('POST', '/watchlist', { code }),
  watchlistRemove: (code) => send('DELETE', `/watchlist/${code}`),
  watchlistImport: (codes) => send('POST', '/watchlist/import', { codes }),
  watchlistClear: () => send('POST', '/watchlist/clear'),
  settings: () => get('/settings'),
  setSetting: (key, value) => send('POST', '/settings', { key, value: String(value) }),
  setSettingsBulk: (items) => send('POST', '/settings/bulk', { items }),
  backupExport: () => get('/backup/export'),
  backupImport: (payload) => send('POST', '/backup/import', { payload }),
  logActions: (items) => send('POST', '/log/action', { items }),
  logsApi: (limit = 80) => get(`/logs/api?limit=${limit}`),
  logsActions: (limit = 80) => get(`/logs/actions?limit=${limit}`),
  logsDatasource: (limit = 80) => get(`/logs/datasource?limit=${limit}`),
  metaStocks: () => get('/meta/stocks'),
  syncStocks: () => send('POST', '/meta/stocks/sync'),
  syncTags: (scope = 'stocks') => send('POST', `/meta/tags/sync?scope=${scope}`),
  syncStatus: () => get('/meta/tags/sync/status'),
  metaLookup: (code) => get(`/meta/lookup/${code}`),
  positions: () => get('/positions'),
  positionSave: (body) => send('PUT', '/positions', body),
  positionDelete: (code) => send('DELETE', `/positions/${code}`),
  positionSnapshotDelete: (id) => send('DELETE', `/positions/snapshots/${id}`),
  positionSnapshotsClear: () => send('DELETE', '/positions/snapshots'),
  positionsSummary: () => get('/positions/summary'),
  positionsLedger: (code = '', limit = 80) =>
    get(`/positions/ledger?limit=${limit}${code ? '&code=' + code : ''}`),
  alerts: () => get('/alerts'),
  alertCreate: (body) => send('POST', '/alerts', body),
  alertUpdate: (id, body) => send('PUT', `/alerts/${id}`, body),
  alertDelete: (id) => send('DELETE', `/alerts/${id}`),
  alertsCheck: () => get('/alerts/check'),
  alertsCheckChanges: () => get('/alerts/check-changes'),
  analysisData: (code) => get(`/stocks/${code}/analysis-data`),
  aiHistory: (code) => get(`/ai/history/${encodeURIComponent(code)}`),
  aiSave: (body) => send('POST', '/ai/save', body),
  baiduSr: (code, ktype = 'day') => get(`/stocks/${code}/baidu-sr?ktype=${ktype}`),
  stockChanges: (limit = 80) => get(`/market/stock-changes?limit=${limit}`),
  stockNews: (code, limit = 10) => get(`/stocks/${code}/news?limit=${limit}`),
  stockAnnouncements: (code, limit = 8) => get(`/stocks/${code}/announcements?limit=${limit}`),

  // 飞书通知
  feishuTest: () => send('POST', '/notify/feishu/test'),

  // 龙虎榜席位
  lhbSeats: () => get('/lhb/seats'),
  lhbSeatsSync: (force = false) => send('POST', '/lhb/seats/sync', { force }),
  lhbSeatCreate: (body) => send('POST', '/lhb/seats', body),
  lhbSeatUpdate: (nickname, body) => send('PUT', `/lhb/seats/${encodeURIComponent(nickname)}`, body),
  lhbSeatDelete: (nickname) => send('DELETE', `/lhb/seats/${encodeURIComponent(nickname)}`),

  // 龙虎榜游资动向
  lhbMovesDates: () => get('/lhb/moves/dates'),
  lhbMoves: (date, side = 'buy') => get(`/lhb/moves?date=${date}&side=${side}`),
  lhbMovesNick: (nickname) => get(`/lhb/moves/${encodeURIComponent(nickname)}`),
  lhbMovesSync: (start, end) => send('POST', '/lhb/moves/sync', { start, end }),
  lhbMovesSyncStatus: () => get('/lhb/moves/sync/status'),
  lhbMovesAuto: (enabled) => send('POST', '/lhb/moves/auto', { enabled }),
  lhbMovesAutoGet: () => get('/lhb/moves/auto'),

  // 盘后选股
  screenerRules: () => get('/screener/rules'),
  screenerSyncBars: (lookback = 120, scope = 'all') =>
    send('POST', '/screener/sync-bars', { lookback_days: lookback, scope }),
  screenerSyncStatus: () => get('/screener/sync-status'),
  screenerRun: (rules, scope = 'all', notifyFeishu = false, params = null) =>
    send('POST', '/screener/run', { rules, scope, notify_feishu: notifyFeishu, params }),
  screenerRuns: (limit = 20) => get(`/screener/runs?limit=${limit}`),
  screenerRunDetail: (id) => get(`/screener/runs/${id}`),
}

/** 基础行情列配置（多个表格复用；数值列可点击排序） */
export const briefColumns = [
  { key: 'name', label: '名称', align: 'left' },
  { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'zhangsu', label: '涨速', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
  { key: 'turnover', label: '换手率', fmt: 'pct', sortable: true },
  { key: 'volume_ratio', label: '量比', sortable: true },
  { key: 'main_inflow', label: '主力净流入', fmt: 'amount', sortable: true },
]
