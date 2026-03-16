import base64
import hmac
import hashlib
import datetime
import requests
from .base import Exchange


class OKX(Exchange):
    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        super().__init__(api_key, api_secret, passphrase)
        self.base_url = "https://www.okx.com"
        self.balance_total = 0.0

    def fetch_balances(self, ccy: str = "") -> list:
        endpoint = "/api/v5/account/balance"
        timestamp = self._get_iso_timestamp()
        params = f"?ccy={ccy}" if ccy else ""
        signature = self._generate_signature(timestamp, "GET", endpoint + params, "")
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        query_params = {"ccy": ccy} if ccy else {}
        response = self._make_request("GET", endpoint, headers=headers, params=query_params)

        data = response.get("data", [])
        self.balance_total = sum(float(d.get("totalEq", 0)) for d in data)
        print(f"OKX Total Balance (USD): {self.balance_total}")

        details = data[0].get("details", []) if data else []
        # print(f"fetch_balances OKX API Response: {response}")
        return [d for d in details if float(d.get("cashBal", 0)) > 0]

    def fetch_position_risk(self, inst_type: str = "") -> list:
        endpoint = "/api/v5/account/account-position-risk"
        timestamp = self._get_iso_timestamp()
        params = f"?instType={inst_type}" if inst_type else ""
        signature = self._generate_signature(timestamp, "GET", endpoint + params, "")
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        query_params = {"instType": inst_type} if inst_type else {}
        response = self._make_request("GET", endpoint, headers=headers, params=query_params)
        # print(f"fetch_position_risk OKX API Response: {response}")
        return response.get("data", [])

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

    def _get_iso_timestamp(self) -> str:
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _generate_signature(self, timestamp: str, method: str, endpoint: str, body: str) -> str:
        message = f"{timestamp}{method}{endpoint}{body}"
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode("utf-8")