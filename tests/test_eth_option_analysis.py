"""
测试 ETH 期权分析脚本 (src/scripts/eth_option_analysis.py)
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# 确保 src 目录在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scripts.eth_option_analysis import (
    calc_daily_swing,
    analyze_swing_probability,
    run_eth_option_analysis,
    fetch_eth_daily_klines,
)


# ---------------------------------------------------------------------------
# 辅助构造函数
# ---------------------------------------------------------------------------

def _make_kline(open_p, high_p, low_p, close_p, start_ms=1_700_000_000_000):
    """构造单根 K 线原始数据（Bybit 格式：[startTime, open, high, low, close, volume, turnover]）。"""
    return [str(start_ms), str(open_p), str(high_p), str(low_p), str(close_p), "1000", "10000"]


def _make_bybit_mock(raw_klines):
    """返回 get_kline 的 mock，raw_klines 按照 Bybit 从新到旧的顺序传入。"""
    mock = MagicMock()
    mock.get_kline.return_value = raw_klines
    return mock


# ---------------------------------------------------------------------------
# fetch_eth_daily_klines
# ---------------------------------------------------------------------------

class TestFetchEthDailyKlines:
    def test_returns_list_sorted_old_to_new(self):
        # Bybit 返回从新到旧：[day3, day2, day1]
        raw = [
            _make_kline(2000, 2100, 1900, 2050, start_ms=1_700_200_000_000),  # 最新
            _make_kline(1900, 2000, 1850, 1980, start_ms=1_700_100_000_000),
            _make_kline(1800, 1900, 1750, 1880, start_ms=1_700_000_000_000),  # 最旧
        ]
        mock_bybit = _make_bybit_mock(raw)
        result = fetch_eth_daily_klines(mock_bybit, days=3)
        # 结果应从旧到新
        assert result[0]["start_ms"] == 1_700_000_000_000
        assert result[-1]["start_ms"] == 1_700_200_000_000

    def test_fields_present(self):
        raw = [_make_kline(1800, 1900, 1750, 1880)]
        mock_bybit = _make_bybit_mock(raw)
        result = fetch_eth_daily_klines(mock_bybit, days=1)
        assert len(result) == 1
        k = result[0]
        for field in ("start_ms", "datetime_utc8", "open", "high", "low", "close", "volume"):
            assert field in k, f"Missing field: {field}"
        # Validate types and ranges
        assert isinstance(k["start_ms"], int)
        assert isinstance(k["open"], float) and k["open"] > 0
        assert isinstance(k["high"], float) and k["high"] >= k["open"]
        assert isinstance(k["low"], float) and k["low"] <= k["open"]
        assert isinstance(k["close"], float) and k["close"] > 0
        # Validate datetime format
        from datetime import datetime
        datetime.strptime(k["datetime_utc8"], "%Y-%m-%d %H:%M")

    def test_calls_get_kline_with_correct_args(self):
        mock_bybit = _make_bybit_mock([])
        fetch_eth_daily_klines(mock_bybit, days=50)
        mock_bybit.get_kline.assert_called_once_with(
            symbol="ETHUSDT", interval="D", limit=50
        )

    def test_days_capped_at_200(self):
        mock_bybit = _make_bybit_mock([])
        fetch_eth_daily_klines(mock_bybit, days=300)
        call_kwargs = mock_bybit.get_kline.call_args[1]
        assert call_kwargs["limit"] == 200


# ---------------------------------------------------------------------------
# calc_daily_swing
# ---------------------------------------------------------------------------

class TestCalcDailySwing:
    def test_swing_calculation(self):
        klines = [
            {"start_ms": 1, "datetime_utc8": "2024-01-01 08:00", "open": 2000.0,
             "high": 2100.0, "low": 1900.0, "close": 2050.0, "volume": 100},
        ]
        result = calc_daily_swing(klines)
        # swing = (2100 - 1900) / 2000 * 100 = 10%
        assert len(result) == 1
        assert result[0]["swing_pct"] == pytest.approx(10.0, rel=1e-4)

    def test_zero_open_skipped(self):
        klines = [
            {"start_ms": 1, "datetime_utc8": "2024-01-01", "open": 0,
             "high": 100, "low": 50, "close": 80, "volume": 10},
        ]
        result = calc_daily_swing(klines)
        assert result == []

    def test_preserves_original_fields(self):
        klines = [
            {"start_ms": 42, "datetime_utc8": "2024-01-02 08:00", "open": 1000.0,
             "high": 1050.0, "low": 980.0, "close": 1020.0, "volume": 200},
        ]
        result = calc_daily_swing(klines)
        assert result[0]["start_ms"] == 42
        assert result[0]["volume"] == 200

    def test_multiple_klines(self):
        klines = [
            {"start_ms": 1, "datetime_utc8": "d1", "open": 1000.0, "high": 1030.0, "low": 970.0,
             "close": 1000.0, "volume": 1},   # swing = 6%
            {"start_ms": 2, "datetime_utc8": "d2", "open": 1000.0, "high": 1020.0, "low": 990.0,
             "close": 1010.0, "volume": 1},   # swing = 3%
        ]
        result = calc_daily_swing(klines)
        assert result[0]["swing_pct"] == pytest.approx(6.0, rel=1e-3)
        assert result[1]["swing_pct"] == pytest.approx(3.0, rel=1e-3)


# ---------------------------------------------------------------------------
# analyze_swing_probability
# ---------------------------------------------------------------------------

class TestAnalyzeSwingProbability:
    def _make_klines(self, swings):
        """根据 swing_pct 列表构造最简 kline 字典列表。"""
        return [
            {
                "start_ms": i,
                "datetime_utc8": f"2024-01-{i+1:02d}",
                "open": 1000.0, "high": 1000 + s * 5, "low": 1000 - s * 5,
                "close": 1000.0, "volume": 1,
                "swing_pct": float(s),
            }
            for i, s in enumerate(swings)
        ]

    def test_empty_returns_error(self):
        result = analyze_swing_probability([])
        assert "error" in result

    def test_prob_exceed_calculation(self):
        # 10 根 K 线，6 根 swing >= 5%
        swings = [6, 7, 8, 5, 5.1, 5.5, 4, 3, 2, 1]
        klines = self._make_klines(swings)
        result = analyze_swing_probability(klines, threshold_pct=5.0)
        assert result["exceed_count"] == 6
        assert result["prob_exceed_pct"] == pytest.approx(60.0)

    def test_low_prob_suggests_sell_put_or_call(self):
        # 全部在 4% 以内 -> 概率 0%
        swings = [1, 2, 3, 4, 2, 1, 3, 2, 1, 2]
        klines = self._make_klines(swings)
        result = analyze_swing_probability(klines, threshold_pct=5.0)
        assert result["prob_exceed_pct"] == 0.0
        assert "Put" in result["recommended_option_type"] or "Call" in result["recommended_option_type"]

    def test_high_prob_suggests_strangle(self):
        # 全部在 6% 以上 -> 概率 100%
        swings = [6, 7, 8, 9, 10, 6, 7, 8, 9, 6]
        klines = self._make_klines(swings)
        result = analyze_swing_probability(klines, threshold_pct=5.0)
        assert result["prob_exceed_pct"] == 100.0
        assert "Strangle" in result["recommended_option_type"]

    def test_result_contains_all_keys(self):
        swings = [3, 4, 6, 2, 5]
        klines = self._make_klines(swings)
        result = analyze_swing_probability(klines, threshold_pct=5.0)
        for key in (
            "symbol", "analysis_period_days", "threshold_pct",
            "exceed_count", "prob_exceed_pct", "prob_exceed_recent_30d_pct",
            "avg_swing_pct", "max_swing_pct", "min_swing_pct",
            "recommended_option_type", "strategy_suggestion", "klines",
        ):
            assert key in result, f"Missing return key: {key}"

    def test_avg_max_min_swing(self):
        swings = [2.0, 4.0, 6.0]
        klines = self._make_klines(swings)
        result = analyze_swing_probability(klines, threshold_pct=5.0)
        assert result["avg_swing_pct"] == pytest.approx(4.0, rel=1e-4)
        assert result["max_swing_pct"] == pytest.approx(6.0, rel=1e-4)
        assert result["min_swing_pct"] == pytest.approx(2.0, rel=1e-4)

    def test_recent_lower_volatility_branch(self):
        """历史高波动但近 30 日波动偏低时，应提示近期平稳并建议卖出 Put/Call。"""
        # 前 50 根高波动（7%），后 30 根低波动（2%）
        swings = [7.0] * 50 + [2.0] * 30
        klines = self._make_klines(swings)
        result = analyze_swing_probability(klines, threshold_pct=5.0)
        # 整体 prob_exceed > 0，近 30 日 prob_exceed_recent = 0
        assert result["prob_exceed_recent_30d_pct"] == 0.0
        assert result["prob_exceed_pct"] > 0.0
        # 整体概率 < 50%? No: 50/80 ≈ 62.5% >= 50, so strangle branch
        # Actually 50 high + 30 low = 80 total, 50 exceed => 62.5% >= 50 -> Strangle
        # Let's use 20 high + 30 low = 50 total, 20 exceed => 40% < 50 -> Sell Put/Call
        swings2 = [7.0] * 20 + [2.0] * 30
        klines2 = self._make_klines(swings2)
        result2 = analyze_swing_probability(klines2, threshold_pct=5.0)
        assert result2["prob_exceed_pct"] == pytest.approx(40.0)
        assert result2["prob_exceed_recent_30d_pct"] == 0.0
        assert "Put" in result2["recommended_option_type"] or "Call" in result2["recommended_option_type"]
        assert "近期波动偏小" in result2["strategy_suggestion"]


# ---------------------------------------------------------------------------
# run_eth_option_analysis (集成)
# ---------------------------------------------------------------------------

class TestRunEthOptionAnalysis:
    def test_end_to_end(self):
        # 构造 20 根 K 线：10 根 swing=6%, 10 根 swing=3%
        raw = []
        base_ms = 1_700_000_000_000
        day_ms = 86400 * 1000
        for i in range(20):
            if i < 10:
                high, low = 1060, 940   # swing ≈ 12%
            else:
                high, low = 1015, 985   # swing ≈ 3%
            raw.append(_make_kline(1000, high, low, 1010, start_ms=base_ms + i * day_ms))

        # Bybit 返回从新到旧
        raw_reversed = list(reversed(raw))
        mock_bybit = _make_bybit_mock(raw_reversed)

        result = run_eth_option_analysis(mock_bybit, days=20, threshold_pct=5.0)
        assert result["analysis_period_days"] == 20
        assert result["exceed_count"] == 10
        assert result["prob_exceed_pct"] == pytest.approx(50.0)
