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


    def get_position_list(
        self,
        category: str,
        symbol: str = None,
        base_coin: str = None,
        settle_coin: str = None,
        limit: int = None,
        cursor: str = None,
    ) -> dict:
        """
        获取仓位信息 GET /v5/position/list

        :param category: 产品类型 linear/inverse/option (必填)
        :param symbol: 交易对名称, 例如 BTCUSDT (可选)
        :param base_coin: 基础币种, 仅适用于 option (可选)
        :param settle_coin: 结算币种, linear/inverse 有效 (可选)
        :param limit: 每页数量, 默认20, 最大200 (可选)
        :param cursor: 游标, 用于翻页 (可选)
        :return: 仓位信息字典
        """
        endpoint = "/v5/position/list"
        timestamp = self._get_timestamp()
        recv_window = "5000"

        params = {"category": category}
        if symbol is not None:
            params["symbol"] = symbol
        if base_coin is not None:
            params["baseCoin"] = base_coin
        if settle_coin is not None:
            params["settleCoin"] = settle_coin
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        signature = self._generate_signature(timestamp, recv_window, params)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }

        response = self._make_request("GET", endpoint, headers=headers, params=params)
        print(f"get_position_list Bybit API Response: {response}")

        return response


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