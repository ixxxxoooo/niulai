<template>
  <div class="card mt16" v-if="news.length || announcements.length">
    <div class="card-title" style="display:flex;align-items:center;gap:10px">
      <div class="tabs mini-tabs" style="margin:0">
        <div class="tab" :class="{active: infoTab==='news'}" @click="infoTab='news'">新闻</div>
        <div class="tab" :class="{active: infoTab==='ann'}" @click="infoTab='ann'">公告</div>
      </div>
    </div>
    <div class="news-list" v-if="infoTab==='news'">
      <div v-for="(n, i) in news" :key="'n'+i" class="news-item clickable" @click="openArticle(n)">
        <div class="news-body">
          <img v-if="n.image" class="news-img" :src="n.image" loading="lazy" />
          <div class="news-text">
            <div class="news-title">{{ n.title }}</div>
            <div class="news-summary" v-if="n.content">{{ n.content.slice(0, 80) }}…</div>
            <div class="news-meta">{{ n.source }} · {{ n.date }}</div>
          </div>
        </div>
      </div>
      <div v-if="!news.length" class="empty-hint">暂无新闻</div>
    </div>
    <div class="news-list" v-if="infoTab==='ann'">
      <div v-for="(n, i) in announcements" :key="'a'+i" class="news-item clickable" @click="openArticle(n)">
        <div class="news-text" style="flex:1">
          <div class="news-title">{{ n.title }}</div>
          <div class="news-meta">{{ n.source }} · {{ n.date }}</div>
        </div>
      </div>
      <div v-if="!announcements.length" class="empty-hint">暂无公告</div>
    </div>
  </div>

  <Teleport to="body">
    <div class="modal-overlay" v-if="articleModal" @click.self="articleModal=null">
      <div class="modal-box article-modal">
        <div class="modal-head">
          <span class="modal-title">{{ articleModal.title }}</span>
          <button class="modal-close" @click="articleModal=null"><UiIcon name="close" :size="16" /></button>
        </div>
        <div class="modal-meta">{{ articleModal.source }} · {{ articleModal.date }}</div>
        <div class="modal-body article-content" v-if="articleContent" v-html="articleContent"></div>
        <div class="modal-body" v-else-if="articleLoading" style="text-align:center;padding:40px;color:var(--text-dim)">加载中…</div>
        <div class="modal-body" v-else style="padding:20px;color:var(--text-dim);line-height:1.7">
          暂无法在浮窗内展示全文（部分公告为 PDF 或站点限制）。请点击下方「查看原文」阅读。
        </div>
        <div class="modal-foot">
          <a :href="articleModal.url" target="_blank" rel="noopener" class="btn-outline">查看原文 <UiIcon name="external" :size="12" /></a>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * 新闻/公告列表与全文浮窗
 * @author ygw
 */
import { ref, watch } from 'vue'

const props = defineProps({
  news: { type: Array, default: () => [] },
  announcements: { type: Array, default: () => [] },
  initialTab: { type: String, default: 'news' },
})

const infoTab = ref(props.initialTab)

watch(() => props.initialTab, (v) => { if (v) infoTab.value = v })
const articleModal = ref(null)
const articleContent = ref('')
const articleLoading = ref(false)

/**
 * 清洗正文 HTML：去掉强制宽高/内联样式，避免浮窗图片撑破布局。
 * @param {string} html
 * @returns {string}
 */
function sanitizeArticleHtml(html) {
  if (!html) return ''
  let s = String(html)
  s = s.replace(/<script[\s\S]*?<\/script>/gi, '')
  s = s.replace(/<style[\s\S]*?<\/style>/gi, '')
  s = s.replace(/<img\b([^>]*)>/gi, (_m, attrs) => {
    let a = String(attrs || '')
    a = a.replace(/\s(width|height|style)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    return `<img${a}>`
  })
  s = s.replace(/\sstyle\s*=\s*("([^"]*)"|'([^']*)')/gi, (m, _q, d, sgl) => {
    const raw = d != null ? d : (sgl || '')
    const cleaned = raw
      .replace(/width\s*:[^;]+;?/gi, '')
      .replace(/max-width\s*:[^;]+;?/gi, '')
      .replace(/min-width\s*:[^;]+;?/gi, '')
      .trim()
    return cleaned ? ` style="${cleaned}"` : ''
  })
  return s
}

async function openArticle(item) {
  articleModal.value = item
  articleContent.value = ''
  articleLoading.value = true
  try {
    const resp = await fetch(`/api/crawl-article?url=${encodeURIComponent(item.url)}`)
    if (resp.ok) {
      const data = await resp.json()
      articleContent.value = sanitizeArticleHtml(data.html || data.content || '')
    }
  } catch (e) { /* fallback */ }
  articleLoading.value = false
}
</script>

<style scoped>
.mini-tabs { margin-bottom: 0; }
.mini-tabs .tab { padding: 3px 12px; font-size: 12px; }
.news-list { display: flex; flex-direction: column; gap: 0; height: 360px; overflow-y: auto; }
.news-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border); }
.news-item:last-child { border-bottom: none; }
.news-body { display: flex; gap: 10px; flex: 1; min-width: 0; }
.news-img { width: 72px; height: 48px; border-radius: 4px; object-fit: cover; flex-shrink: 0; }
.news-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.news-title { font-size: 13px; color: var(--text); line-height: 1.4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.news-summary { font-size: 12px; color: var(--text-dim); line-height: 1.4; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.news-meta { font-size: 11px; color: var(--text-dim); }
.news-item.clickable { cursor: pointer; transition: background .15s; }
.news-item.clickable:hover { background: var(--bg-hover, rgba(0,0,0,.03)); }
.empty-hint { font-size: 13px; color: var(--text-dim); padding: 20px 0; text-align: center; }
.modal-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,.5); z-index: 1000; display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: var(--bg-card); border-radius: 12px; padding: 20px; width: 90%; max-width: 600px;
  max-height: 80vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,.3);
}
.modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
.modal-title { font-size: 15px; font-weight: 600; color: var(--text); line-height: 1.5; }
.modal-close { border: none; background: transparent; font-size: 18px; color: var(--text-dim); cursor: pointer; padding: 4px; display: inline-flex; align-items: center; justify-content: center; }
.modal-meta { font-size: 12px; color: var(--text-dim); margin-bottom: 12px; }
.modal-body { font-size: 14px; color: var(--text); line-height: 1.7; }
.article-modal { max-width: 700px; max-height: 85vh; }
.article-content { word-break: break-word; overflow-x: hidden; }
.article-content :deep(img),
.article-content :deep(video),
.article-content :deep(iframe),
.article-content :deep(table) {
  max-width: 100% !important;
  width: auto !important;
  height: auto !important;
  display: block;
  margin: 10px auto;
  border-radius: 4px;
  object-fit: contain;
}
.article-content :deep(p) { margin: 8px 0; }
.article-content :deep(table) { border-collapse: collapse; }
.modal-foot { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border); text-align: right; }
.btn-outline { display: inline-block; padding: 6px 16px; border: 1px solid var(--accent); color: var(--accent); border-radius: 6px; font-size: 13px; text-decoration: none; }
.btn-outline:hover { background: var(--accent); color: #fff; text-decoration: none; }
</style>
