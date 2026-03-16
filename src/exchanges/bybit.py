import hmac
import hashlib
import time
import urllib.parse
import requests
from .base import Exchange


class Bybit(Exchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.bybit.com"
        self.balance_total = 0.0

    

    def fetch_wallet_balance(self, account_type: str = "UNIFIED") -> dict:
        endpoint = "/v5/account/wallet-balance"
        timestamp = self._get_timestamp()
        recv_window = "5000"
        params = {
            "accountType": account_type,
        }
        signature = self._generate_signature(timestamp, recv_window, params)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }
        response = self._make_request("GET", endpoint, headers=headers, params=params)
        print(f"fetch_wallet_balance Bybit API Response: {response}")

        return response

    def fetch_asset_overview(self) -> dict:
        endpoint = "/v5/asset/asset-overview"
        timestamp = self._get_timestamp()
        recv_window = "5000"
        params = {}
        signature = self._generate_signature(timestamp, recv_window, params)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }
        response = self._make_request("GET", endpoint, headers=headers, params=params)
        # print(f"fetch_asset_overview Bybit API Response: {response}")

        result = response.get("result", {})
        self.balance_total = float(result.get("totalEquity", 0))
        print(f"Bybit Total Asset Value (USD): {self.balance_total}")

        return result

    def _make_request(self, method, endpoint, headers, params=None, body=None):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=headers, params=params, json=body)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}, Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            raise

    def _generate_signature(self, timestamp: int, recv_window: str, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        param_str = f"{timestamp}{self.api_key}{recv_window}{query_string}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _get_timestamp(self):
        return int(time.time() * 1000)