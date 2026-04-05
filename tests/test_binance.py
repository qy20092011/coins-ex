import os
import sys
from dotenv import load_dotenv

# Add the parent directory of 'exchanges' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from exchanges.binance import Binance

# 加载 .env 文件中的环境变量
load_dotenv()

def test_binance_balance():
    try:
        binance = Binance(api_key=os.getenv('BINANCE_API_KEY'), api_secret=os.getenv('BINANCE_API_SECRET'))

        binance.fetch_wallet_balance()

        print(f"Binance Total Balance (USD): {binance.balance_total}")
    except Exception as e:
        print(f"Error testing Binance balance: {e}")

if __name__ == "__main__":
    test_binance_balance()
