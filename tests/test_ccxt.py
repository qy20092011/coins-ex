import ccxt
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

def fetch_binance_unified_account_balances():
    # Binance API keys
    binance_api_key = os.getenv('BINANCE_API_KEY')
    binance_secret = os.getenv('BINANCE_API_SECRET')

    # 初始化 Binance 交易所
    binance = ccxt.binance({
        'apiKey': binance_api_key,
        'secret': binance_secret,
        'options': {
            'defaultType': 'future',  # 确保使用统一账户模式
        },
    })

    # 获取 Binance 统一账户资产
    try:
        binance_balances = binance.fetch_balance({'type': 'future'})
        print("Binance Unified Account Balances:")
        print(binance_balances)
    except Exception as e:
        print(f"Error fetching Binance unified account balances: {e}")

def fetch_balances():
    # Bybit API keys
    bybit_api_key = 'BYBIT_API_KEY'
    bybit_secret = 'BYBIT_API_SECRET'

    # Binance API keys
    binance_api_key = 'BINANCE_API_KEY'
    binance_secret = 'BINANCE_API_SECRET'

    # Initialize Bybit exchange
    bybit = ccxt.bybit({
        'apiKey': bybit_api_key,
        'secret': bybit_secret,
    })

    # Initialize Binance exchange
    binance = ccxt.binance({
        'apiKey': binance_api_key,
        'secret': binance_secret,
    })

    # Fetch Bybit balances
    try:
        bybit_balances = bybit.fetch_balance()
        print("Bybit Balances:")
        print(bybit_balances)
    except Exception as e:
        print(f"Error fetching Bybit balances: {e}")

    # Fetch Binance balances
    try:
        binance_balances = binance.fetch_balance()
        print("Binance Balances:")
        print(binance_balances)
    except Exception as e:
        print(f"Error fetching Binance balances: {e}")

if __name__ == "__main__":
    fetch_binance_unified_account_balances()
    fetch_balances()