import os
import sys
import time
import threading
import schedule
import uvicorn
from fastapi import FastAPI
from exchanges.binance import Binance
from exchanges.okx import OKX
from exchanges.bybit import Bybit
from exchanges.bitget import Bitget
from exchanges.hyperliquid import Hyper

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.logger import setup_logger, get_logger
from scripts.monitor_option import monitor_option_positions
from scripts.eth_option_analysis import run_eth_option_analysis

app = FastAPI()

# 模块级 logger（此时日志系统未初始化，仅占位）
logger = get_logger("main")

total_balance = 0.0
binance = okx = bybit = bitget = hyper = None

def fetch_total_balance():
    global total_balance
    binance.fetch_wallet_balance()
    okx.fetch_balances()
    bybit.fetch_asset_overview()
    bitget.fetch_account_assets()
    hyper.fetch_wallet_balance()

    total_balance = (
        binance.balance_total + okx.balance_total +
        bybit.balance_total + bitget.balance_total +
        hyper.balance_total
    )
    logger.info(f"Total Balance across all exchanges (USD): {int(total_balance)}")
    return total_balance

@app.get("/asset/all")
def get_total_balance():
    fetch_total_balance()
    return {"total_balance": int(total_balance), "currency": "USD", "exchanges": [
        {"ex": "Binance", "balance": int(binance.balance_total)},
        {"ex": "OKX", "balance": int(okx.balance_total)},
        {"ex": "Bybit", "balance": int(bybit.balance_total)},
        {"ex": "Bitget", "balance": int(bitget.balance_total)},
        {"ex": "Hyperliquid", "balance": int(hyper.balance_total)}
    ]}

@app.get("/analysis/eth-option")
def get_eth_option_analysis(days: int = 200, threshold_pct: float = 5.0):
    """
    分析 ETH 日线 K 线，以 16:00 (UTC+8) 为 session 基准，
    计算每日最大涨跌幅及超过阈值的历史概率，给出期权策略建议。
    """
    result = run_eth_option_analysis(bybit, days=days, threshold_pct=threshold_pct)
    return result

def run_scheduler():
    schedule.every(60).seconds.do(fetch_total_balance)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    global binance, okx, bybit, bitget, hyper

    from dotenv import load_dotenv
    load_dotenv()

    # ① 最先初始化日志系统，接管 uvicorn/fastapi 日志
    setup_logger()
    logger.info("========== 应用启动 ==========")

    # ② 初始化交易所客户端
    try:
        binance = Binance(api_key=os.getenv('BINANCE_API_KEY'), api_secret=os.getenv('BINANCE_API_SECRET'))
        logger.info("Binance 初始化完成")

        okx = OKX(api_key=os.getenv('OKX_API_KEY'), api_secret=os.getenv('OKX_API_SECRET'), passphrase=os.getenv('OKX_PASSPHRASE'))
        logger.info("OKX 初始化完成")

        bybit = Bybit(api_key=os.getenv('BYBIT_API_KEY'), api_secret=os.getenv('BYBIT_API_SECRET'))
        logger.info("Bybit 初始化完成")

        bitget = Bitget(api_key=os.getenv('BITGET_API_KEY'), api_secret=os.getenv('BITGET_API_SECRET'), passphrase=os.getenv('BITGET_PASSPHRASE'))
        logger.info("Bitget 初始化完成")

        hyper = Hyper(api_key=os.getenv('HYPER_API_KEY'), api_secret=os.getenv('HYPER_API_SECRET'))
        logger.info("Hyperliquid 初始化完成")

    except Exception as e:
        logger.exception(f"交易所客户端初始化失败: {e}")
        sys.exit(1)

    # ③ 启动定时任务线程
    # scheduler_thread = threading.Thread(
    #     target=run_scheduler,
    #     daemon=True,
    #     name="Scheduler"
    # )
    # scheduler_thread.start()
    # logger.info("定时任务线程已启动")

    # ④ 启动期权仓位监控线程
    option_monitor_thread = threading.Thread(
        target=monitor_option_positions,
        args=(bybit, 10),
        daemon=True,
        name="OptionMonitor"
    )
    option_monitor_thread.start()
    logger.info("期权监控线程已启动")

    # ⑤ 启动 uvicorn，log_config=None 让其继承 root logger
    logger.info("启动 HTTP 服务 0.0.0.0:8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None
    )

if __name__ == "__main__":
    main()