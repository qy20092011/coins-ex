import os
from dotenv import load_dotenv

load_dotenv()

EXCHANGES_CONFIG = {
    "binance": {
        "api_key": os.getenv("BINANCE_API_KEY", ""),
        "api_secret": os.getenv("BINANCE_SECRET", ""),
        "api_endpoint": "https://api.binance.com/api/v3"
    },
    "okx": {
        "api_key": os.getenv("OKX_API_KEY", ""),
        "api_secret": os.getenv("OKX_SECRET", ""),
        "passphrase": os.getenv("OKX_PASSPHRASE", ""),
        "api_endpoint": "https://www.okx.com/api/v5"
    },
    "bybit": {
        "api_key": os.getenv("BYBIT_API_KEY", ""),
        "api_secret": os.getenv("BYBIT_SECRET", ""),
        "api_endpoint": "https://api.bybit.com/v2"
    },
    "bitget": {
        "api_key": os.getenv("BITGET_API_KEY", ""),
        "api_secret": os.getenv("BITGET_SECRET", ""),
        "passphrase": os.getenv("BITGET_PASSPHRASE", ""),
        "api_endpoint": "https://api.bitget.com/api/v1"
    },
}
