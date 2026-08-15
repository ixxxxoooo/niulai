#!/usr/bin/env python3
"""数据链路验证脚本：打印各数据源真实数据（无需启动 Web 服务）

用法: .venv/bin/python scripts/verify.py [--stock 600519]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.datasource import eastmoney, tencent  # noqa: E402
from backend.analyzer import market as market_an   # noqa: E402


def fmt_amount(v):
    if v is None:
        return "-"
    if abs(v) >= 1e12:
        return f"{v/1e12:.2f}万亿"
    if abs(v) >= 1e8:
        return f"{v/1e8:.1f}亿"
    if abs(v) >= 1e4:
        return f"{v/1e4:.1f}万"
    return f"{v:.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock", default="600519", help="个股代码")
    args = ap.parse_args()

    c = eastmoney.get_client()

    print("=" * 60)
    print("1. 大盘指数")
    for q in c.index_quotes():
        print(f"  {q.name:6s} {q.price:>10.2f} {q.change_pct:>7.2f}%  "
              f"成交额 {fmt_amount(q.amount)}  涨{q.up_count}/跌{q.down_count}/平{q.flat_count}")

    print("=" * 60)
    print("2. 行业板块 TOP5（涨幅）")
    for s in c.sector_list("industry", 5):
        print(f"  {s.name:10s} {s.change_pct:>7.2f}%  主力 {fmt_amount(s.main_inflow)}  "
              f"涨{s.up_count}/跌{s.down_count}  领涨 {s.leader_name} {s.leader_pct}%")

    print("=" * 60)
    print("3. 概念板块 TOP5（主力净流入）")
    for s in c.sector_moneyflow("concept", 5):
        print(f"  {s.name:12s} 主力净流入 {fmt_amount(s.main_inflow):>10s}  {s.change_pct:>7.2f}%")

    print("=" * 60)
    print("4. 涨速榜 TOP8")
    for s in c.zhangsu_rank(8):
        print(f"  {s.code} {s.name:8s} 现价 {s.price:>8.2f} 涨速 {s.zhangsu:>6.2f}% "
              f"涨幅 {s.change_pct:>6.2f}%")

    print("=" * 60)
    print("5. 主力净流入榜 TOP8")
    for s in c.moneyflow_rank(8):
        print(f"  {s.code} {s.name:8s} 主力净流入 {fmt_amount(s.main_inflow):>10s} "
              f"占比 {s.main_inflow_pct}% 涨幅 {s.change_pct}%")

    print("=" * 60)
    print("6. 热门股榜（成交额 TOP5）")
    for s in c.hot_stocks("amount", 5):
        print(f"  {s.code} {s.name:8s} 成交额 {fmt_amount(s.amount)} 涨幅 {s.change_pct}%")

    print("=" * 60)
    print("7. 涨停池（前 5）")
    try:
        for p in c.limit_up_pool(5):
            print(f"  {p.code} {p.name:8s} {p.price:>8.2f} {p.change_pct:>6.2f}% "
                  f"连板{p.lbc} 封单 {fmt_amount(p.seal_amount)} 首封 {p.first_time}")
    except eastmoney.EastMoneyError as e:
        print(f"  涨停池获取失败: {e}")

    print("=" * 60)
    print(f"8. 个股详情 {args.stock}（东财快照 + 腾讯盘口）")
    em = eastmoney.get_client()
    snap = em.stock_snapshot(args.stock)
    if snap:
        tq = tencent.get_client().fetch_quotes([args.stock]).get(snap.code, {})
        print(f"  {snap.name} ({snap.code}) 现价 {snap.price} 涨跌幅 {snap.change_pct}% "
              f"换手 {snap.turnover}% 量比 {snap.volume_ratio}")
        ob = tq.get("orderbook", {})
        print(f"  买一 {ob.get('bid', [{}])[0].get('price') if ob.get('bid') else '-'} / "
              f"卖一 {ob.get('ask', [{}])[0].get('price') if ob.get('ask') else '-'}  "
              f"外盘 {tq.get('outer')} 内盘 {tq.get('inner')} 委差 {tq.get('weicha')} "
              f"均价 {tq.get('avg_price')}")
        print(f"  涨停 {snap.limit_up} 跌停 {snap.limit_down} 总市值 {fmt_amount(snap.total_mv)} "
              f"PE {snap.pe} PB {snap.pb}")
    else:
        print("  个股快照获取失败")

    print("=" * 60)
    print(f"9. 分时数据 {args.stock}（点数: 最近10条）")
    t = c.intraday_trends(args.stock)
    if t:
        print(f"  昨收 {t.pre_close} 共 {len(t.points)} 点")
        for p in t.points[-10:]:
            print(f"    {p.time} 价 {p.price} 均价 {p.avg} 量 {p.volume}手 额 {fmt_amount(p.amount)}")

    print("=" * 60)
    print(f"10. 成交明细 {args.stock}（最近 5 条）")
    for tk in c.stock_ticks(args.stock, limit=5):
        d = {1: "买", 2: "卖", 0: "-"}.get(tk.direction, "?")
        print(f"    {tk.time} 价 {tk.price} 量 {tk.volume}手 方向[{d}]")

    print("=" * 60)
    print(f"11. 资金流历史 {args.stock}（5日）")
    for m in c.moneyflow_history(args.stock, days=5):
        print(f"    {m.date} 主力净流入 {fmt_amount(m.main_inflow)}")

    print("=" * 60)
    ov = market_an.market_overview()
    print("12. 大盘概况聚合")
    print(f"  两市成交额 {fmt_amount(ov.total_amount)}  涨 {ov.up_count}/跌 {ov.down_count}/平 {ov.flat_count}")
    print(f"  涨停 {ov.limit_up_count} 家  盘中: {ov.is_trading_time}  数据时间: {ov.quote_time}")


if __name__ == "__main__":
    main()
