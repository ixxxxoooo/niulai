<template>
  <div class="card">
    <div style="display:flex; align-items: baseline; gap: 20px; flex-wrap: wrap;">
      <span class="stock-price" :class="pctClass(detail.change_pct)">{{ fmtPrice(detail.price) }}</span>
      <span class="stock-change" :class="pctClass(detail.change_pct)">
        {{ fmtPct(detail.change_pct) }}　{{ detail.change != null ? (detail.change > 0 ? '+' : '') + fmtNum(detail.change) : '-' }}
      </span>
      <span style="color: var(--text-dim); font-size: 13px; display:inline-flex; align-items:center; gap:6px; flex-wrap:wrap">
        今开 {{ fmtPrice(detail.open) }} · 昨收 {{ fmtPrice(detail.prev_close) }}
        <span
          v-for="t in signalTags"
          :key="t.label"
          class="signal-tag has-tooltip"
          :class="[t.cls, { clickable: t.to }]"
          @click="t.to && navigate(t.to)"
        >{{ t.label }}<span class="tag-tooltip">{{ t.desc }}</span></span>
      </span>
      <span style="margin-left:auto; color: var(--text-dim); font-size: 13px">
        <b class="up">涨停 {{ fmtPrice(detail.limit_up) }}</b>　<b class="down">跌停 {{ fmtPrice(detail.limit_down) }}</b>
      </span>
    </div>
    <div class="kv-grid mt12">
      <div class="kv"><span class="k">最高</span><span class="v up">{{ fmtPrice(detail.high) }}</span></div>
      <div class="kv"><span class="k">最低</span><span class="v down">{{ fmtPrice(detail.low) }}</span></div>
      <div class="kv"><span class="k" data-tip="振幅 = (当日最高 - 最低) ÷ 昨收。振幅大说明多空分歧激烈、波动大；振幅小说明方向未明，观望为宜。">振幅</span><span class="v" :class="pctClass(detail.amplitude)">{{ fmtPct(detail.amplitude) }}</span></div>
      <div class="kv"><span class="k" data-tip="换手率 = 当日成交量 ÷ 流通股本，代表筹码换手活跃度。1~3% 正常；5% 以上活跃；10% 以上高换手，可能有资金博弈或出货风险。低位高换手是吸筹，高位高换手要警惕。">换手率</span><span class="v">{{ fmtPct(detail.turnover) }}</span></div>
      <div class="kv"><span class="k" data-tip="量比 = 当前每分钟平均成交量 ÷ 过去5日每分钟平均量。>1.5 说明明显放量、资金活跃；<0.8 说明缩量、观望为主。盘中看它比看绝对量更直观。">量比</span>
        <span class="v">
          {{ fmtNum(detail.volume_ratio) }}
          <span v-if="detail.volume_ratio != null && detail.volume_ratio > 1.5" class="vol-badge up">放量</span>
          <span v-else-if="detail.volume_ratio != null && detail.volume_ratio < 0.8" class="vol-badge down">缩量</span>
          <span v-else-if="detail.volume_ratio != null" class="vol-badge flat">平量</span>
        </span>
      </div>
      <div class="kv"><span class="k" data-tip="量能 = 今日成交量 ÷ 前5日均量。放量说明资金大幅进场，缩量说明观望。关键看配合：上涨放量健康，下跌放量要警惕。">量能(较5日均量)</span>
        <span class="v" :class="vol5Class">{{ vol5Text }}</span>
      </div>
      <div class="kv"><span class="k" data-tip="成交量 = 当天成交的手数（1手 = 100股）。和成交额配合看：放量上涨健康，放量下跌危险。">成交量</span><span class="v">{{ fmtAmount((detail.volume || 0) * 100) }}股</span></div>
      <div class="kv"><span class="k" data-tip="成交额 = 当天买卖双方实际成交总金额。市场活跃度的核心指标：量大才有人气，放量才有行情。">成交额</span><span class="v">{{ fmtAmount(detail.amount) }}</span></div>
      <div class="kv"><span class="k" data-tip="外盘 = 以卖价成交的量（主动买入，买家出手抢筹）。外盘 > 内盘说明买盘主动，盘面偏强。">外盘</span><span class="v up">{{ fmtNum(detail.outer, 0) }}</span></div>
      <div class="kv"><span class="k" data-tip="内盘 = 以买价成交的量（主动卖出，卖家砸盘）。内盘 > 外盘说明抛压主动，盘面偏弱。">内盘</span><span class="v down">{{ fmtNum(detail.inner, 0) }}</span></div>
      <div class="kv"><span class="k" data-tip="委差 = 买一到买五挂单总量 - 卖一到卖五挂单总量。正数买盘挂单多（偏强），负数卖压大（偏弱）。注意大单可能挂而不成，仅作参考。">委差</span><span class="v" :class="pctClass(detail.weicha)">{{ fmtNum(detail.weicha, 0) }}</span></div>
      <div class="kv"><span class="k" data-tip="均价 = 累计成交额 ÷ 累计成交量（当日平均成本）。现价高于均价说明今天买入的人整体浮盈、盘面强势；低于均价说明多数人套着，偏弱。">均价</span><span class="v">{{ fmtPrice(detail.avg_price) }}</span></div>
      <div class="kv"><span class="k" data-tip="市盈率 = 股价 ÷ 每股收益。估值高低要跟同行业比：低PE不代表便宜，高PE也不代表贵。">市盈率(动)</span><span class="v">{{ fmtNum(detail.pe) }}</span></div>
      <div class="kv"><span class="k" data-tip="市净率 = 股价 ÷ 每股净资产。银行、地产等重资产行业常用：<1 破净，>10 说明溢价很高。">市净率</span><span class="v">{{ fmtNum(detail.pb) }}</span></div>
      <div class="kv"><span class="k">总市值</span><span class="v">{{ fmtAmount(detail.total_mv) }}</span></div>
      <div class="kv"><span class="k">流通市值</span><span class="v">{{ fmtAmount(detail.float_mv) }}</span></div>
      <div class="kv"><span class="k" data-tip="主力净流入 = 超大单 + 大单净额（按单笔成交额估算的「大资金」动向）。净流入 > 0 说明大资金在买，< 0 在卖。注意这是估算值，大单可能拆单规避。">主力净流入</span><span class="v" :class="pctClass(detail.main_inflow)">{{ fmtAmount(detail.main_inflow) }}</span></div>
    </div>
    <div class="mt12" v-if="conceptList.length">
      <div style="font-size:12px;color:var(--text-dim);margin-bottom:6px">板块概念</div>
      <div class="concept-tags">
        <span class="concept-tag" v-for="c in conceptList" :key="c" :title="`查看板块：${c}`" @click="gotoConcept(c)">{{ c }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 个股实时快照：价格、信号标签、关键指标、概念
 * @author ygw
 */
import { fmtAmount, fmtPrice, fmtPct, fmtNum, pctClass } from '../../utils.js'
import { api } from '../../api.js'
import { navigate } from '../../router.js'

const props = defineProps({
  detail: { type: Object, default: () => ({}) },
  signalTags: { type: Array, default: () => [] },
  vol5Text: { type: String, default: '—' },
  vol5Class: { type: String, default: 'flat' },
  conceptList: { type: Array, default: () => [] },
})

async function gotoConcept(name) {
  try {
    const res = await api.sectorConceptCode(name)
    if (res && res.code) navigate(`/sector/${res.code}`)
  } catch (e) { /* 无映射时忽略 */ }
}
</script>

<style scoped>
.vol-badge {
  display: inline-block; font-size: 10px; font-weight: 700;
  border-radius: 3px; padding: 0 4px; margin-left: 4px; vertical-align: 2px;
}
.vol-badge.up { background: var(--up-bg); color: var(--up); }
.vol-badge.down { background: var(--down-bg); color: var(--down); }
.vol-badge.flat { background: rgba(139, 148, 158, 0.15); color: var(--text-dim); }
.signal-tag.clickable { cursor: pointer; }
.signal-tag.clickable:hover { filter: brightness(1.1); box-shadow: 0 0 0 1px currentColor; }
</style>
