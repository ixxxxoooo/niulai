"""健康检查/设置/日志/元数据/文章爬取
@author ygw
"""
import time

from fastapi import APIRouter, HTTPException, Query

from ... import config
from ...analyzer import schedule
from ...db.tags import infer_board
from ...db import store as db

from .common import SettingBody, SettingsBulkBody, ActionLogBody

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok", "time": time.strftime("%Y-%m-%d %H:%M:%S")}


@router.get("/trading/time")
def trading_time():
    now = time.localtime()
    return {
        "is_trading_time": schedule.is_trading_time(),
        "is_trading_day": schedule.is_trading_day(__import__("datetime").date(*now[:3])),
        "session": schedule.session_label(),
    }


@router.get("/settings")
def settings_get():
    """读取全部设置"""
    return {"items": db.get_settings()}


@router.post("/settings")
def settings_post(body: SettingBody):
    """写入单条设置"""
    if not body.key:
        raise HTTPException(status_code=400, detail="key 不能为空")
    db.set_setting(body.key, body.value)
    return {"ok": True, "items": db.get_settings()}


@router.post("/settings/bulk")
def settings_bulk(body: SettingsBulkBody):
    """批量写入设置（用于 localStorage 迁移）"""
    db.set_settings(body.items or {})
    return {"ok": True, "items": db.get_settings()}


@router.post("/log/action")
def log_action(body: ActionLogBody):
    """前端行为日志上报"""
    for it in (body.items or [])[:50]:
        if not isinstance(it, dict):
            continue
        db.log_action(
            str(it.get("action") or "unknown"),
            str(it.get("target") or ""),
            str(it.get("detail") or ""),
            str(it.get("ts") or ""),
        )
    return {"ok": True}


@router.get("/logs/api")
def logs_api(limit: int = Query(100, ge=1, le=500)):
    return db.list_api_logs(limit)


@router.get("/logs/actions")
def logs_actions(limit: int = Query(100, ge=1, le=500)):
    return db.list_action_logs(limit)


@router.get("/logs/datasource")
def logs_datasource(limit: int = Query(100, ge=1, le=500)):
    return db.list_ds_logs(limit)


@router.get("/meta/stocks")
def meta_stocks():
    """股票列表同步状态"""
    st = None
    try:
        from ...db.sync import sync_status
        st = sync_status()
    except Exception:
        st = None
    return {
        "count": db.stock_count(),
        "updated_at": db.stocks_updated_at(),
        "lastConceptSyncAt": db.get_setting("lastConceptSyncAt"),
        "autoSyncHours": db.get_setting("autoSyncHours") or "0",
        "sync": st,
    }


@router.get("/meta/lookup/{code}")
def meta_lookup(code: str):
    """本地 SQLite 即时查名称/行业/概念（详情页秒出名称）。"""
    code = (code or "").strip()
    m = db.get_stock(code)
    if m:
        return m
    b, st = infer_board(code, "")
    return {
        "code": code, "name": "", "industry": "", "concepts": "",
        "board": b, "is_st": st, "classify": "AStock",
    }


@router.post("/meta/stocks/sync")
def meta_stocks_sync():
    """手动触发全 A 股列表同步（后台任务 + 进度）。"""
    from ...db.sync import start_sync_job
    return {"ok": True, **start_sync_job("stocks")}


@router.post("/meta/tags/sync")
def meta_tags_sync(scope: str = Query("stocks", pattern="^(stocks|concepts|all)$")):
    """后台同步标签，立即返回；用 GET /meta/tags/sync/status 看进度。"""
    from ...db.sync import start_sync_job
    return {"ok": True, **start_sync_job(scope)}


@router.get("/meta/tags/sync/status")
def meta_tags_sync_status():
    """同步进度。"""
    from ...db.sync import sync_status
    st = sync_status()
    st["count"] = db.stock_count()
    st["updated_at"] = db.stocks_updated_at()
    st["lastConceptSyncAt"] = db.get_setting("lastConceptSyncAt")
    return st


@router.post("/notify/feishu/test")
def notify_feishu_test():
    """飞书推送测试：发送一条示例卡片验证 Webhook 配置。"""
    from ...notify.feishu import send_test
    return send_test()


# ── 申万行业分类（2021 版，AKShare 免费同步入库） ──

@router.get("/meta/sw/count")
def meta_sw_count():
    """申万行业库状态（行业数/股票映射数/是否在同步）。"""
    from ...db.sw_industry import sw_count, sync_status
    return {"stock_count": sw_count(), "sync": sync_status()}


@router.post("/meta/sw/sync")
def meta_sw_sync():
    """后台启动申万行业分类同步（首次约数分钟）。"""
    from ...db.sw_industry import start_sw_sync
    return start_sw_sync()


@router.get("/meta/sw/sync/status")
def meta_sw_sync_status():
    """申万行业同步进度。"""
    from ...db.sw_industry import sw_count, sync_status
    st = sync_status()
    st["stock_count"] = sw_count()
    return st


@router.get("/meta/sw/industries")
def meta_sw_industries(level: int = Query(1, ge=1, le=3), parent: str = Query("", max_length=32)):
    """申万行业字典（按级别/父级过滤，股票数降序）。"""
    from ...db.sw_industry import list_sw_industries
    return {"items": list_sw_industries(level, parent)}


@router.get("/meta/sw/stocks")
def meta_sw_stocks(code: str = Query(..., min_length=6, max_length=32),
                   limit: int = Query(500, ge=1, le=1000)):
    """某申万行业（一级/二级/三级 code 均可）的成分股。"""
    from ...db.sw_industry import list_sw_stocks
    return {"items": list_sw_stocks(code, limit)}


@router.get("/meta/sw/stock/{code}")
def meta_sw_stock(code: str):
    """个股申万行业映射。"""
    from ...db.sw_industry import stock_sw
    data = stock_sw(code)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到 {code} 的申万行业")
    return data


# ── 东财板块表（行业 + 概念 元数据入库） ──

@router.get("/meta/sectors")
def meta_sectors(type: str = Query("", pattern="^(|industry|concept)$")):
    """板块表（东财行业 + 概念）。"""
    from ...db.sectors import list_sectors, sector_count
    return {"count": sector_count(), "items": list_sectors(type)}


@router.post("/meta/sectors/sync")
def meta_sectors_sync():
    """同步东财板块表元数据。"""
    from ...db.sectors import sync_sectors, sector_count
    r = sync_sectors()
    r["count"] = sector_count()
    return r


@router.get("/crawl-article")
def crawl_article(url: str = Query(...)):
    """
    爬取新闻/公告全文 HTML 内容（提取正文区域，保留图片）。
    东财公告详情页多为空壳，优先走公告内容 API。
    @author ygw
    """
    import html as html_lib
    import httpx, re, logging
    logger = logging.getLogger("crawl_article")
    from fastapi.responses import JSONResponse

    if not url or not url.startswith("http"):
        return JSONResponse({"html": "", "error": "无效URL"}, status_code=400)

    headers = {"User-Agent": config.USER_AGENT, "Referer": "https://data.eastmoney.com/"}

    def _clean_html(content: str) -> str:
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.S)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.S)
        content = re.sub(r'src="(/[^"]+)"', lambda m: f'src="https://data.eastmoney.com{m.group(1)}"', content)
        while True:
            n = re.sub(
                r'(<img\b[^>]*?)\s(?:width|height)\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)',
                r'\1',
                content,
                count=1,
                flags=re.I,
            )
            if n == content:
                break
            content = n
        content = re.sub(r'(<img\b[^>]*?)\sstyle\s*=\s*("[^"]*"|\'[^\']*\')', r'\1', content, flags=re.I)
        return content.strip()

    def _text_to_html(text: str) -> str:
        parts = []
        for para in re.split(r'\n+', text or ''):
            para = para.strip()
            if para:
                parts.append(f'<p>{html_lib.escape(para)}</p>')
        return ''.join(parts)

    # 东财公告：优先内容 API（详情页 notice_content 常为空，正文在接口里）
    art_m = (
        re.search(r'/(AN\d{10,})\.html', url, re.I)
        or re.search(r'[?&](?:infocode|art_code)=(AN\d{10,})', url, re.I)
    )
    if art_m:
        art_code = art_m.group(1).upper()
        try:
            api_url = (
                'https://np-cnotice-stock.eastmoney.com/api/content/ann'
                f'?art_code={art_code}&client_source=web&page_index=1'
            )
            api_resp = httpx.get(api_url, headers=headers, timeout=10)
            data = (api_resp.json() or {}).get('data') or {}
            text = (data.get('notice_content') or '').strip()
            pdf = (data.get('attach_url_web') or data.get('attach_url') or '').strip()
            body = _text_to_html(text)
            if pdf:
                body += (
                    f'<p style="margin-top:16px"><a href="{html_lib.escape(pdf)}" '
                    f'target="_blank" rel="noopener">查看 PDF 原文 ↗</a></p>'
                )
            if body:
                return {"html": body, "url": url, "pdf": pdf, "source": "eastmoney_ann_api"}
        except Exception as e:
            logger.warning(f"公告内容 API 失败 art_code={art_code} err={e}")

    try:
        resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        page = resp.text or resp.content.decode("utf-8", errors="ignore")

        content = ""
        for pat in (
            r'<div[^>]*id="ContentBody"[^>]*>([\s\S]*?)</div>\s*<div',
            r'<div[^>]*class="[^"]*newsContent[^"]*"[^>]*>([\s\S]*?)</div>\s*<div',
            r'<div[^>]*class="[^"]*txtinfos[^"]*"[^>]*>([\s\S]*?)</div>\s*<div',
            r'<div[^>]*id="notice_content"[^>]*>([\s\S]*?)</div>',
            r'<div[^>]*class="[^"]*content_text[^"]*"[^>]*>([\s\S]*?)</div>',
            r'<article[^>]*>([\s\S]*?)</article>',
        ):
            m = re.search(pat, page, re.I)
            if m and len(m.group(1).strip()) > 40:
                content = m.group(1)
                break
        if not content:
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', page, re.S)
            if paragraphs:
                content = ''.join(f'<p>{p}</p>' for p in paragraphs[:50])

        content = _clean_html(content)
        return {"html": content, "url": url}
    except Exception as e:
        logger.warning(f"爬取文章失败: url={url} err={e}")
        return JSONResponse({"html": "", "error": str(e)}, status_code=200)
