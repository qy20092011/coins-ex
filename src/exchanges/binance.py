import urllib.parse
import hmac
import hashlib
import time
import requests
from exchanges.base import Exchange


class Binance(Exchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.binance.com"
        self.balance_total = 0.0

    def fetch_wallet_balance(self) -> list:
        endpoint = "/sapi/v1/asset/wallet/balance"
        timestamp = self._get_timestamp()
        params = {
            "timestamp": timestamp,
            "quoteAsset": "USDT"
        }
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        response = self._make_request("GET", endpoint, params, headers)

        self.balance_total = sum(float(w['balance']) for w in response if w.get('activate'))
        
        print(f"Binance Total Balance (USD): {self.balance_total}")

        # print(f"fetch_wallet_balance Binance API Response: {response}")  # 调试输出完整响应

        return response

    def fetch_balances(self) -> list:
        endpoint = "/api/v3/account"
        timestamp = self._get_timestamp()
        params = {"timestamp": timestamp}
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        response = self._make_request("GET", endpoint, params, headers)

        print(f"fetch_balances Binance API Response: {response}")  # 调试输出完整响应

        # balances = response.get("balances", [])
        # 过滤余额大于 0 的资产
        # return [b for b in balances if float(b.get("free", 0)) + float(b.get("locked", 0)) > 0]

    def _make_request(self, method, endpoint, params, headers):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}, Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            raise

    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _get_timestamp(self):
        return int(time.time() * 1000)