// K线全局缓存：避免重复请求日K/周K/月K数据（分钟级不变）
// @author ygw
import { api } from '../api.js'

const _cache = new Map()
const CACHE_TTL = 60000 // 60秒缓存

function cacheKey(code, period) {
  return `${code}:${period}`
}

/**
 * 获取K线数据（优先读缓存）
 * @param {string} code 股票代码或指数secid
 * @param {string} period day|week|month
 * @param {number} limit 数据条数
 * @param {boolean} isGlobal 是否全球指数
 * @returns {Promise<object|null>}
 */
export async function getCachedKline(code, period, limit = 350, isGlobal = false) {
  const key = cacheKey(code, period)
  const hit = _cache.get(key)
  if (hit && Date.now() - hit.ts < CACHE_TTL && (hit.data?.points?.length || 0) >= limit) {
    return hit.data
  }

  let data
  if (isGlobal) {
    data = await api.quoteKline(code, period, limit)
  } else {
    data = await api.kline(code, period, limit)
  }
  if (data && data.points && data.points.length) {
    if (hit && (hit.data?.points?.length || 0) > data.points.length && Date.now() - hit.ts < CACHE_TTL) {
      return hit.data
    }
    _cache.set(key, { data, ts: Date.now() })
  }
  return data
}

export function invalidateKline(code, period) {
  _cache.delete(cacheKey(code, period))
}
