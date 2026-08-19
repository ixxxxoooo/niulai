// 自选股与多分组管理（SQLite），内存缓存供全局星标与分组展示
// @author ygw
import { reactive } from 'vue'
import { api } from '../api.js'
import { logAction } from './useActionLog.js'

const SAVED_GROUP_KEY = 'niulai_watchlist_current_group'

export const watchState = reactive({
  codes: [],            // 当前选中分组下的股票代码列表（null 时为全量自选代码）
  allCodes: [],         // 全量所有分组去重代码列表（用于全局 isWatched 判断）
  groups: [],           // 分组列表 [{ id, name, sort_order, count }]
  currentGroupId: null, // 当前选中的分组 ID（null 表示「全部」）
  loaded: false,
})

// 读取上次记录的 group_id
try {
  const saved = localStorage.getItem(SAVED_GROUP_KEY)
  if (saved !== null && saved !== '' && saved !== 'all') {
    watchState.currentGroupId = Number(saved)
  }
} catch (e) { /* ignore */ }

/**
 * 切换当前查看的分组（内存 0ms 即时响应，无缝丝滑）
 * @param {number|null} groupId null 为全部
 */
export function setCurrentGroup(groupId) {
  watchState.currentGroupId = groupId != null ? Number(groupId) : null
  if (watchState.currentGroupId === null) {
    if (watchState.allCodes.length) {
      watchState.codes = [...watchState.allCodes]
    }
  } else {
    const targetGroup = watchState.groups.find(g => g.id === watchState.currentGroupId)
    if (targetGroup && Array.isArray(targetGroup.codes)) {
      watchState.codes = [...targetGroup.codes]
    }
  }
  try {
    if (watchState.currentGroupId != null) {
      localStorage.setItem(SAVED_GROUP_KEY, String(watchState.currentGroupId))
    } else {
      localStorage.setItem(SAVED_GROUP_KEY, 'all')
    }
  } catch (e) { /* ignore */ }
}

/**
 * 从后端加载自选列表及分组元数据
 * @param {number|null} groupId 可选指定分组 ID
 */
export async function loadWatchlist(groupId = undefined) {
  const targetGid = groupId !== undefined ? groupId : watchState.currentGroupId
  const r = await api.watchlist(targetGid)
  watchState.groups = r.groups || []
  
  // 聚合全量代码
  const allGroupCodes = (watchState.groups || []).flatMap(g => g.codes || [])
  const allSet = new Set([...(r.codes || []), ...allGroupCodes, ...watchState.allCodes])
  watchState.allCodes = [...allSet]

  if (targetGid === null) {
    watchState.codes = r.codes || []
  } else {
    const targetGroup = watchState.groups.find(g => g.id === targetGid)
    watchState.codes = (targetGroup && targetGroup.codes) ? targetGroup.codes : (r.codes || [])
  }
  watchState.loaded = true
  return watchState.codes
}

/**
 * 重新拉取分组列表
 */
export async function loadGroups() {
  const r = await api.watchlistGroups()
  watchState.groups = r.groups || []
  return watchState.groups
}

/**
 * 判断某只股票是否在自选股中（全量）
 */
export function isWatched(code) {
  if (watchState.allCodes.length) {
    return watchState.allCodes.includes(code)
  }
  return watchState.codes.includes(code)
}

/**
 * 加入自选
 * @param {string} code 6 位代码
 * @param {number|null} groupId 目标分组 ID（默认当前选中分组或默认分组）
 */
export async function addWatch(code, groupId = undefined) {
  if (!code) return
  const gid = groupId !== undefined ? groupId : (watchState.currentGroupId || 1)
  const r = await api.watchlistAdd(code, gid)
  if (!watchState.codes.includes(code)) watchState.codes.push(code)
  if (!watchState.allCodes.includes(code)) watchState.allCodes.push(code)
  if (r.groups) watchState.groups = r.groups
  logAction('watch_add', code, `group=${gid}`)
}

/**
 * 从指定分组或全部自选中移出
 * @param {string} code 6 位代码
 * @param {number|null} groupId 若为 null 则从全部移除
 */
export async function removeWatch(code, groupId = undefined) {
  const gid = groupId !== undefined ? groupId : watchState.currentGroupId
  const r = await api.watchlistRemove(code, gid)
  if (gid === null) {
    watchState.codes = watchState.codes.filter(c => c !== code)
    watchState.allCodes = watchState.allCodes.filter(c => c !== code)
  } else {
    watchState.codes = watchState.codes.filter(c => c !== code)
    // 重新确认全量
    api.watchlist(null).then(res => {
      watchState.allCodes = res.codes || []
    }).catch(() => {})
  }
  if (r.groups) watchState.groups = r.groups
  logAction('watch_remove', code, `group=${gid}`)
}

export async function toggleWatch(code, groupId = undefined) {
  if (isWatched(code)) await removeWatch(code, groupId)
  else await addWatch(code, groupId)
}

/**
 * 清空自选
 * @param {number|null} groupId 为空清空全部
 */
export async function clearWatch(groupId = undefined) {
  const gid = groupId !== undefined ? groupId : watchState.currentGroupId
  const r = await api.watchlistClear(gid)
  if (gid === null) {
    watchState.codes = []
    watchState.allCodes = []
  } else {
    watchState.codes = []
    api.watchlist(null).then(res => {
      watchState.allCodes = res.codes || []
    }).catch(() => {})
  }
  if (r.groups) watchState.groups = r.groups
  logAction('watch_clear', '', `group=${gid}`)
}

export async function importWatch(codes, groupId = undefined) {
  const gid = groupId !== undefined ? groupId : (watchState.currentGroupId || 1)
  const r = await api.watchlistImport(codes, gid)
  watchState.codes = r.codes || []
  if (r.groups) watchState.groups = r.groups
  api.watchlist(null).then(res => {
    watchState.allCodes = res.codes || []
  }).catch(() => {})
  logAction('watch_import', '', `count=${watchState.codes.length},group=${gid}`)
  return watchState.codes
}

/**
 * 创建新分组
 */
export async function createGroup(name) {
  const r = await api.watchlistGroupCreate(name)
  if (r.groups) watchState.groups = r.groups
  logAction('watch_group_create', name)
  return r.group
}

/**
 * 重命名分组
 */
export async function renameGroup(groupId, name) {
  const r = await api.watchlistGroupUpdate(groupId, { name })
  if (r.groups) watchState.groups = r.groups
  logAction('watch_group_rename', name, `id=${groupId}`)
}

/**
 * 删除分组
 */
export async function deleteGroup(groupId) {
  const r = await api.watchlistGroupDelete(groupId)
  if (r.groups) watchState.groups = r.groups
  if (watchState.currentGroupId === groupId) {
    setCurrentGroup(null)
  }
  logAction('watch_group_delete', '', `id=${groupId}`)
}

/**
 * 调整分组排序
 */
export async function reorderGroups(groupIds) {
  const r = await api.watchlistGroupReorder(groupIds)
  if (r.groups) watchState.groups = r.groups
  logAction('watch_group_reorder')
}

/**
 * 获取股票所属分组 ID 列表
 */
export async function getStockGroups(code) {
  const r = await api.watchlistStockGroups(code)
  return r.group_ids || []
}

/**
 * 设置股票所属分组
 */
export async function setStockGroups(code, groupIds) {
  const r = await api.watchlistSetStockGroups(code, groupIds)
  if (r.groups) watchState.groups = r.groups
  // 重新同步全量
  api.watchlist(null).then(res => {
    watchState.allCodes = res.codes || []
  }).catch(() => {})
  logAction('watch_stock_groups', code, `groups=${groupIds.join(',')}`)
}

/**
 * 初始化热门预设分组
 */
export async function initPresetGroups() {
  const r = await api.watchlistInitPresets()
  if (r.groups) watchState.groups = r.groups
  if (r.codes) {
    watchState.allCodes = r.codes
    if (watchState.currentGroupId === null) {
      watchState.codes = r.codes
    }
  }
  logAction('watch_init_presets')
  return r
}

