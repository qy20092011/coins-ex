import os
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

app = FastAPI()

total_balance = 0.0
binance = okx = bybit = bitget = hyper = None

def fetch_total_balance():
    global total_balance
    binance.fetch_wallet_balance()
    okx.fetch_balances()
    bybit.fetch_asset_overview()
    bitget.fetch_account_assets()
    hyper.fetch_wallet_balance()

    total_balance = binance.balance_total + okx.balance_total + bybit.balance_total + bitget.balance_total + hyper.balance_total
    print(f"Total Balance across all exchanges (USD): {int(total_balance)}")
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

def run_scheduler():
    schedule.every(60).seconds.do(fetch_total_balance)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    global binance, okx, bybit, bitget, hyper

    from dotenv import load_dotenv
    load_dotenv()

    binance = Binance(api_key=os.getenv('BINANCE_API_KEY'), api_secret=os.getenv('BINANCE_API_SECRET'))
    okx = OKX(api_key=os.getenv('OKX_API_KEY'), api_secret=os.getenv('OKX_API_SECRET'), passphrase=os.getenv('OKX_PASSPHRASE'))
    bybit = Bybit(api_key=os.getenv('BYBIT_API_KEY'), api_secret=os.getenv('BYBIT_API_SECRET'))
    bitget = Bitget(api_key=os.getenv('BITGET_API_KEY'), api_secret=os.getenv('BITGET_API_SECRET'), passphrase=os.getenv('BITGET_PASSPHRASE'))
    hyper = Hyper(api_key=os.getenv('HYPER_API_KEY'), api_secret=os.getenv('HYPER_API_SECRET'))

    # Run scheduler in background thread
    # thread = threading.Thread(target=run_scheduler, daemon=True)
    # thread.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()