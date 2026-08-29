"""7x24 实时财经电报与快讯数据源（财联社主源 + 东财快讯备源）。
@author ygw
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

# 财联社分类映射
CLS_CATEGORY_MAP = {
    "all": "",
    "red": "red",
    "company": "company",
    "watch": "watch",
    "hk_us": "hk_us",
    "fund": "fund",
}


def get_cls_sign(params: Dict[str, Any]) -> str:
    """计算财联社 API 签名: SHA1(sorted_qs) -> MD5。"""
    keys = sorted(params.keys())
    qs = "&".join(f"{k}={params[k]}" for k in keys)
    sha1_val = hashlib.sha1(qs.encode("utf-8")).hexdigest()
    return hashlib.md5(sha1_val.encode("utf-8")).hexdigest()


class TelegraphClient:
    """7x24 财经电报与快讯客户端（多源融合与容错降级）。"""

    def __init__(self, timeout: float = 6.0):
        self._timeout = timeout
        self._http = httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            },
            follow_redirects=True,
        )

    def fetch_cls(
        self,
        category: str = "all",
        last_time: Optional[int] = None,
        rn: int = 30,
    ) -> List[Dict[str, Any]]:
        """拉取财联社电报。"""
        url = "https://www.cls.cn/v1/roll/get_roll_list"
        cat_code = CLS_CATEGORY_MAP.get(category, "")
        params: Dict[str, Any] = {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "8.7.9",
            "rn": min(max(rn, 10), 50),
            "refresh_type": 1 if not last_time else 2,
        }
        if cat_code:
            params["category"] = cat_code
        if last_time:
            params["last_time"] = int(last_time)

        params["sign"] = get_cls_sign(params)

        try:
            resp = self._http.get(
                url,
                params=params,
                headers={"Referer": "https://www.cls.cn/telegraph"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("errno") == 0:
                    roll_data = (data.get("data") or {}).get("roll_data") or []
                    return self._normalize_cls(roll_data)
        except Exception as e:
            logger.warning("财联社电报拉取失败: %s", e)
        return []

    def fetch_eastmoney(self, page_size: int = 30) -> List[Dict[str, Any]]:
        """备用源：拉取东方财富快讯。"""
        url = f"https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_{page_size}_1_.html"
        try:
            resp = self._http.get(
                url,
                headers={"Referer": "https://kuaixun.eastmoney.com/"},
            )
            if resp.status_code == 200:
                text = resp.text
                if "ajaxResult=" in text:
                    text = text.split("ajaxResult=", 1)[1].rstrip(";")
                data = json.loads(text)
                items = data.get("LivesList") or []
                return self._normalize_eastmoney(items)
        except Exception as e:
            logger.warning("东财快讯拉取失败: %s", e)
        return []

    def fetch_telegraph(
        self,
        category: str = "all",
        last_time: Optional[int] = None,
        rn: int = 30,
    ) -> List[Dict[str, Any]]:
        """获取电报列表（优先财联社，失败时自动降级到东财快讯）。"""
        items = self.fetch_cls(category=category, last_time=last_time, rn=rn)
        if items:
            return items

        # 降级备源
        logger.info("财联社电报不可用，启用东财快讯备用源降级")
        return self.fetch_eastmoney(page_size=rn)

    def _normalize_cls(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for it in raw_items:
            ctime = it.get("ctime") or int(time.time())
            # 格式化日期与时间
            try:
                struct_t = time.localtime(ctime)
                time_str = time.strftime("%H:%M:%S", struct_t)
                date_str = time.strftime("%Y-%m-%d", struct_t)
                full_time = time.strftime("%Y-%m-%d %H:%M:%S", struct_t)
            except Exception:
                time_str = ""
                date_str = ""
                full_time = ""

            title = str(it.get("title") or "").strip()
            content = str(it.get("content") or "").strip()
            if not title and content:
                # 尝试从【...】中提取标题
                m = re.match(r"^【(.*?)】", content)
                if m:
                    title = m.group(1)

            level = str(it.get("level") or "").upper()
            is_red = level in ("A", "B") or bool(it.get("is_red")) or (title and ("【" in title or "重大" in title or "紧急" in title))

            # 主题标签
            subjects = []
            for s in (it.get("subjects") or []):
                s_name = s.get("subject_name")
                if s_name and s_name not in subjects:
                    subjects.append(s_name)

            # 关联股票
            stocks = []
            for stk in (it.get("stocks") or []):
                code = stk.get("symbol") or stk.get("code")
                name = stk.get("name")
                if code and name:
                    stocks.append({
                        "code": str(code).split(".")[0],
                        "name": str(name),
                        "change_pct": stk.get("change_pct") or stk.get("change"),
                    })

            results.append({
                "id": str(it.get("id") or ctime),
                "title": title,
                "content": content,
                "time": time_str,
                "date": date_str,
                "full_time": full_time,
                "timestamp": ctime,
                "is_red": is_red,
                "level": level,
                "source": "财联社",
                "subjects": subjects,
                "stocks": stocks,
                "share_url": it.get("share_url") or (f"https://www.cls.cn/detail/{it.get('id')}" if it.get("id") else ""),
            })
        return results

    def _normalize_eastmoney(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for it in raw_items:
            showtime = str(it.get("showtime") or "")
            title = str(it.get("title") or it.get("simtitle") or "").strip()
            content = str(it.get("digest") or it.get("simdigest") or "").strip()
            if not title and content:
                m = re.match(r"^【(.*?)】", content)
                if m:
                    title = m.group(1)

            time_str = showtime[11:19] if len(showtime) >= 19 else showtime
            date_str = showtime[:10] if len(showtime) >= 10 else ""

            try:
                ts = int(time.mktime(time.strptime(showtime, "%Y-%m-%d %H:%M:%S"))) if showtime else int(time.time())
            except Exception:
                ts = int(time.time())

            is_red = "重大" in title or "突发" in title or "国务院" in title or "央行" in title or "证监会" in title

            results.append({
                "id": str(it.get("id") or it.get("newsid") or ts),
                "title": title,
                "content": content,
                "time": time_str,
                "date": date_str,
                "full_time": showtime,
                "timestamp": ts,
                "is_red": is_red,
                "level": "B" if is_red else "C",
                "source": "东财快讯",
                "subjects": [],
                "stocks": [],
                "share_url": it.get("url_w") or it.get("url_m") or "",
            })
        return results


# 全局单例
_client: Optional[TelegraphClient] = None


def get_telegraph_client() -> TelegraphClient:
    global _client
    if _client is None:
        _client = TelegraphClient()
    return _client
