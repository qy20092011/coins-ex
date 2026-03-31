"""
ETH 期权分析脚本

以每日 16:00 (UTC+8) 为日线 K 线的开始和结束，
从 Bybit 获取 ETHUSDT 历史日线 K 线数据，分析每日最大涨跌幅，
计算涨跌幅超过 5% 的历史概率，并给出卖出期权（Put/Call）策略建议。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# UTC+8 时区
_TZ_UTC8 = timezone(timedelta(hours=8))

# 日线对齐的基准小时（UTC+8 16:00 = UTC 08:00）
_SESSION_HOUR_UTC8 = 16
_SESSION_HOUR_UTC = _SESSION_HOUR_UTC8 - 8  # = 8


def _session_start_ms(date_utc8: datetime) -> int:
    """返回给定 UTC+8 日期当天 16:00 对应的 UTC 毫秒时间戳（作为当天 session 开盘）。"""
    dt = date_utc8.replace(hour=_SESSION_HOUR_UTC8, minute=0, second=0, microsecond=0,
                           tzinfo=_TZ_UTC8)
    return int(dt.timestamp() * 1000)


def _utc8_day_start_ms(days_ago: int = 0) -> int:
    """当前 UTC+8 日期往前 days_ago 天，返回当天 00:00:00 UTC+8 的毫秒时间戳。"""
    now = datetime.now(_TZ_UTC8)
    target = (now - timedelta(days=days_ago)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int(target.timestamp() * 1000)


def fetch_eth_daily_klines(bybit_client, days: int = 200) -> List[Dict[str, Any]]:
    """
    获取 ETHUSDT 日线 K 线数据。

    Bybit 日线 K 线以 UTC 00:00 为基准，但每日 ETH 期权结算以 08:00 UTC（= 16:00 UTC+8）
    为基准。因此我们拉取日线数据后，附带每根 K 线对应的 UTC+8 开盘时间，
    以便后续对齐分析。

    :param bybit_client: Bybit 实例
    :param days: 拉取的天数，最多 200（单次接口上限）
    :return: K 线字典列表，按时间从早到晚排序
    """
    raw = bybit_client.get_kline(
        symbol="ETHUSDT",
        interval="D",
        limit=min(days, 200),
    )
    # Bybit 返回的列表按时间从新到旧排列，逆序让其从旧到新
    klines = []
    for item in reversed(raw):
        start_ms = int(item[0])
        open_price = float(item[1])
        high_price = float(item[2])
        low_price = float(item[3])
        close_price = float(item[4])
        volume = float(item[5])

        # K 线开盘时间（UTC）-> UTC+8
        dt_utc = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
        dt_utc8 = dt_utc.astimezone(_TZ_UTC8)

        klines.append({
            "start_ms": start_ms,
            "datetime_utc8": dt_utc8.strftime("%Y-%m-%d %H:%M"),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        })
    return klines


def calc_daily_swing(klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    计算每根 K 线的日内最大涨跌幅（high-low）/ open * 100%。

    这代表了在该 session 内价格最多可能的波动范围，用于期权策略分析。

    :param klines: fetch_eth_daily_klines 返回的列表
    :return: 追加了 swing_pct 字段的新列表
    """
    result = []
    for k in klines:
        if k["open"] == 0:
            continue
        swing_pct = (k["high"] - k["low"]) / k["open"] * 100
        result.append({**k, "swing_pct": round(swing_pct, 4)})
    return result


def analyze_swing_probability(
    klines_with_swing: List[Dict[str, Any]],
    threshold_pct: float = 5.0,
) -> Dict[str, Any]:
    """
    统计日内最大涨跌幅超过阈值的历史概率，
    并根据概率给出期权策略建议。

    策略逻辑：
    - 若超过阈值的概率 >= 50%，意味着大波动频繁，适合卖出
      宽跨式期权（Sell Strangle：同时卖出虚值 Put 和虚值 Call），
      或等待大波动后再建仓。
    - 若超过阈值的概率 < 50%，意味着大幅波动较少，价格多在
      5% 以内震荡，可安心卖出较近行权价的 Put 或 Call 以获取权利金。

    :param klines_with_swing: calc_daily_swing 返回的列表
    :param threshold_pct: 判断大幅波动的阈值（默认 5%）
    :return: 分析结果字典
    """
    if not klines_with_swing:
        return {
            "error": "无可用 K 线数据",
            "threshold_pct": threshold_pct,
        }

    swings = [k["swing_pct"] for k in klines_with_swing]
    total = len(swings)
    exceed_count = sum(1 for s in swings if s >= threshold_pct)
    prob_exceed = round(exceed_count / total * 100, 2)
    avg_swing = round(sum(swings) / total, 4)
    max_swing = round(max(swings), 4)
    min_swing = round(min(swings), 4)

    # 近 30 日统计
    recent = swings[-30:] if len(swings) >= 30 else swings
    recent_exceed = sum(1 for s in recent if s >= threshold_pct)
    prob_exceed_recent = round(recent_exceed / len(recent) * 100, 2)

    # 策略建议
    if prob_exceed >= 50:
        strategy = (
            f"历史大幅波动（≥{threshold_pct}%）概率达 {prob_exceed}%，波动频繁。"
            "此时期权隐含波动率（IV）通常偏高，权利金丰厚，"
            "适合卖出宽跨式期权（Sell Strangle）：同时卖出较深虚值 Put 和 Call，"
            "行权价设在当前价格 ±5% 以上，以获取更高权利金并留出足够安全边际。"
            "注意：波动率高时风险亦高，务必设置止损并控制仓位规模。"
        )
        option_type = "Strangle (Sell Put + Sell Call)"
    else:
        # 价格多在阈值内震荡，卖出期权胜率更高
        if prob_exceed_recent < prob_exceed:
            # 近期更加平稳
            strategy = (
                f"整体大幅波动（≥{threshold_pct}%）概率为 {prob_exceed}%，"
                f"近 30 日仅 {prob_exceed_recent}%，近期波动偏小。"
                "建议卖出虚值 Put（看涨时）或虚值 Call（看跌时）以获取权利金，"
                "行权价可设在当前价格 ±5% 附近。"
            )
        else:
            strategy = (
                f"大幅波动（≥{threshold_pct}%）概率为 {prob_exceed}%，低于 50%。"
                "可卖出虚值 Put（看涨时）或虚值 Call（看跌时）以获取权利金，"
                "行权价建议设在当前价格 ±5% 附近。"
            )
        option_type = "Sell Put or Sell Call"

    return {
        "symbol": "ETHUSDT",
        "analysis_period_days": total,
        "threshold_pct": threshold_pct,
        "exceed_count": exceed_count,
        "prob_exceed_pct": prob_exceed,
        "prob_exceed_recent_30d_pct": prob_exceed_recent,
        "avg_swing_pct": avg_swing,
        "max_swing_pct": max_swing,
        "min_swing_pct": min_swing,
        "recommended_option_type": option_type,
        "strategy_suggestion": strategy,
        "klines": klines_with_swing,
    }


def run_eth_option_analysis(bybit_client, days: int = 200, threshold_pct: float = 5.0) -> Dict[str, Any]:
    """
    完整执行 ETH 期权分析流程的入口函数。

    :param bybit_client: Bybit 实例
    :param days: 拉取天数
    :param threshold_pct: 大幅波动阈值（%），默认 5.0
    :return: 分析结果字典
    """
    klines = fetch_eth_daily_klines(bybit_client, days=days)
    klines_with_swing = calc_daily_swing(klines)
    return analyze_swing_probability(klines_with_swing, threshold_pct=threshold_pct)
