import base64
import hmac
import hashlib
import time
import requests
from .base import Exchange


class Bitget(Exchange):
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        super().__init__(api_key, api_secret, passphrase)
        self.base_url = "https://api.bitget.com"
        self.balance_total = 0.0

    def fetch_account_assets(self, asset_type: str = "") -> list:
        endpoint = "/api/v3/account/assets"
        timestamp = self._get_timestamp()
        params = f"?assetType={asset_type}" if asset_type else ""
        signature = self._generate_signature(timestamp, "GET", endpoint + params, "")
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": str(timestamp),
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        query_params = {"assetType": asset_type} if asset_type else {}
        response = self._make_request("GET", endpoint, headers=headers, params=query_params)
        # print(f"fetch_account_assets Bitget API Response: {response}")

        data = response.get("data", {})
        self.balance_total = float(data.get("accountEquity", 0))
        print(f"Bitget Total Account Assets (USD): {self.balance_total}")

        return data

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

    def _generate_signature(self, timestamp: int, method: str, endpoint: str, body: str) -> str:
        message = f"{timestamp}{method}{endpoint}{body}"
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)