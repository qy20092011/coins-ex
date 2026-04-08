import time
import logging
import os
import json
import redis
from logging.handlers import TimedRotatingFileHandler

# 在函数外部或类级别维护峰值记录字典
peak_pnl_pct: dict[str, float] = {}   # key: f"{symbol}_{side}"

def _setup_monitor_logger() -> logging.Logger:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("monitor_option")
    logger.setLevel(logging.DEBUG)
    # 不向上传播到 root logger
    logger.propagate = False

    # 避免重复添加
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 独立日志文件
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "monitor_option.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    logger.addHandler(file_handler)

    return logger

logger = _setup_monitor_logger()

def monitor_option_positions(bybit_client, interval: int = 20):
    """
    定时轮询 Bybit 期权仓位，当 unrealisedPnl < -150 时市价只减仓平仓
    :param bybit_client: Bybit 实例
    :param interval: 轮询间隔（秒），默认 20 秒
    """
    logger.info("期权仓位监控已启动")

    r = redis.Redis(host='39.108.108.214', port=6379, db=0, password='foobaredredis')

    while True:
        try:
            positions = bybit_client.get_position_list(category="option")
            position_list = positions.get("result", {}).get("list", [])
            option_config = json.loads(r.get('user:15:option').decode('utf-8'))

            PEAK_PROFIT_THRESHOLD = float(option_config.get("peakProfit", 0.5))  # 盈亏百分比达到此值时记录峰值
            TRAIL_STOP_THRESHOLD = float(option_config.get("trailStop", 0.1))  # 从峰值回撤达到此值时触发止损

            for pos in position_list:
                symbol = pos.get("symbol")
                side = pos.get("side")
                size = pos.get("size")
                # unrealised_pnl = float(pos.get("unrealisedPnl", 0))
                avg_price = float(pos.get("avgPrice", 0))
                mark_price = float(pos.get("markPrice", 0))

                if not size or float(size) == 0:
                    continue

                if avg_price <= 0 or mark_price <= 0:
                    logger.warning(f"[跳过] {symbol} avgPrice={avg_price} 或 markPrice={mark_price} 无效")
                    continue

                # logger.debug(f"仓位检查: {symbol} side={side} size={size} unrealisedPnl={unrealised_pnl:.2f}")

                # 根据方向计算盈亏百分比
                if side == "Buy":
                    pnl_pct = (mark_price - avg_price) / avg_price
                elif side == "Sell":
                    pnl_pct = (avg_price - mark_price) / avg_price
                else:
                    logger.warning(f"[跳过] {symbol} 未知方向 side={side}")
                    continue

                # 追踪止损 ==========
                pos_key = f"{symbol}_{side}"
                current_peak = peak_pnl_pct.get(pos_key, 0.0)
                # 更新峰值盈利记录
                if pnl_pct > current_peak:
                    peak_pnl_pct[pos_key] = pnl_pct
                    # logger.info(
                    #     f"[峰值更新] {pos_key} 新峰值盈利={pnl_pct:.2%}"
                    # )
                    current_peak = pnl_pct

                # 追踪止损判断：峰值曾超过50%，且当前盈利回撤至<=10%
                should_stop = (
                    current_peak >= PEAK_PROFIT_THRESHOLD
                    and pnl_pct <= TRAIL_STOP_THRESHOLD
                )

                # logger.debug(
                #     f"仓位检查: {symbol} side={side} size={size} "
                #     f"avgPrice={avg_price} markPrice={mark_price} "
                #     f"pnl_pct={pnl_pct*100:.2f}%"
                #     f"peak={current_peak:.2%} should_stop={should_stop}"
                # )

                # 正常止损 ==========
                loss_limit = float(option_config.get("lossLimitPct", -0.5))
                should_stop_loss = pnl_pct <= loss_limit

                if should_stop or should_stop_loss:
                    SLIPPAGE = float(option_config.get("closeSlippage", 0.05))  # 5% 滑点容忍

                    if side == "Buy":
                        close_side = "Sell"
                        limit_price = round(mark_price * (1 - SLIPPAGE), 1)
                    else:
                        close_side = "Buy"
                        limit_price = round(mark_price * (1 + SLIPPAGE), 1)

                    logger.warning(
                        f"[止损触发] {symbol} side={side} pnl_pct={pnl_pct:.2%} "
                        f"markPrice={mark_price} limitPrice={limit_price}"
                    )

                    close_side = "Sell" if side == "Buy" else "Buy"

                    try:
                        response = bybit_client.create_order(
                            category="option",
                            symbol=symbol,
                            side=close_side,
                            orderType="Limit",
                            qty=size,
                            price=str(limit_price),
                            timeInForce="IOC",       # 立即成交否则取消
                            reduceOnly=True
                        )
                        ret_code = response.get("retCode")
                        if ret_code == 0:
                            logger.info(f"[平仓成功] {symbol} 限价平仓订单已提交, orderId={response.get('result', {}).get('orderId')}")
                        else:
                            logger.error(f"[平仓失败] {symbol} retCode={ret_code}, msg={response.get('retMsg')}")
                    except Exception as e:
                        logger.exception(f"[平仓异常] {symbol}: {e}")

        except Exception as e:
            logger.exception(f"[监控异常] 轮询仓位时出错: {e}")

        time.sleep(interval)