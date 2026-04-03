import time
import logging
import os
import json
import redis
from logging.handlers import TimedRotatingFileHandler

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

def monitor_option_positions(bybit_client, interval: int = 30):
    """
    定时轮询 Bybit 期权仓位，当 unrealisedPnl < -150 时市价只减仓平仓
    :param bybit_client: Bybit 实例
    :param interval: 轮询间隔（秒），默认 30 秒
    """
    logger.info("期权仓位监控已启动")

    r = redis.Redis(host='39.108.108.214', port=6379, db=0, password='foobaredredis')

    while True:
        try:
            positions = bybit_client.get_position_list(category="option")
            position_list = positions.get("result", {}).get("list", [])
            option_config = json.loads(r.get('user:15:option').decode('utf-8'))

            for pos in position_list:
                symbol = pos.get("symbol")
                side = pos.get("side")
                size = pos.get("size")
                unrealised_pnl = float(pos.get("unrealisedPnl", 0))
                avg_price = float(pos.get("avgPrice", 0))
                mark_price = float(pos.get("markPrice", 0))

                if not size or float(size) == 0:
                    continue

                if avg_price <= 0 or mark_price <= 0:
                    logger.warning(f"[跳过] {symbol} avgPrice={avg_price} 或 markPrice={mark_price} 无效")
                    continue

                # logger.debug(f"仓位检查: {symbol} side={side} size={size} unrealisedPnl={unrealised_pnl:.2f}")

                # 根据方向计算亏损百分比
                if side == "Buy":
                    pnl_pct = (mark_price - avg_price) / avg_price
                elif side == "Sell":
                    pnl_pct = (avg_price - mark_price) / avg_price
                else:
                    logger.warning(f"[跳过] {symbol} 未知方向 side={side}")
                    continue

                # logger.debug(
                #     f"仓位检查: {symbol} side={side} size={size} "
                #     f"avgPrice={avg_price} markPrice={mark_price} "
                #     f"pnl_pct={pnl_pct*100:.2f}%"
                # )

                loss_limit = float(option_config.get("lossLimitPct", -0.5))

                if pnl_pct <= loss_limit:
                    logger.warning(
                        f"[止损触发] {symbol} side={side} size={size} "
                        f"avgPrice={avg_price} markPrice={mark_price} "
                        f"亏损={pnl_pct*100:.2f}%，执行市价平仓"
                    )

                # if unrealised_pnl < float(option_config.get("unrealisedPnlLimit", -150)):
                #     logger.warning(
                #         f"[止损触发] {symbol} unrealisedPnl={unrealised_pnl:.2f}, "
                #         f"side={side}, size={size}，执行市价平仓"
                #     )

                    close_side = "Sell" if side == "Buy" else "Buy"

                    try:
                        response = bybit_client.create_order(
                            category="option",
                            symbol=symbol,
                            side=close_side,
                            order_type="Market",
                            qty=size,
                            reduce_only=True
                        )
                        ret_code = response.get("retCode")
                        if ret_code == 0:
                            logger.info(f"[平仓成功] {symbol} 市价平仓订单已提交, orderId={response.get('result', {}).get('orderId')}")
                        else:
                            logger.error(f"[平仓失败] {symbol} retCode={ret_code}, msg={response.get('retMsg')}")
                    except Exception as e:
                        logger.exception(f"[平仓异常] {symbol}: {e}")

        except Exception as e:
            logger.exception(f"[监控异常] 轮询仓位时出错: {e}")

        time.sleep(interval)