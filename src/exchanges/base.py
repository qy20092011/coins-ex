import time
import hmac
import hashlib
import urllib.parse
import requests


class Exchange:
    def __init__(self, api_key: str, api_secret: str, passphrase: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = ""

    def fetch_wallet_balance(self):
        raise NotImplementedError("子类必须实现 fetch_wallet_balance 方法")

    def fetch_balances(self):
        raise NotImplementedError("子类必须实现 fetch_balances 方法")

    def get_balance(self, asset):
        balances = self.fetch_balances()
        return balances.get(asset, 0)

    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)

    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _make_request(self, method: str, endpoint: str, params: dict = None, headers: dict = None):
        url = self.base_url + endpoint
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            # print(f"_make_request response: {response}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败 [{self.__class__.__name__}]: {e}")
            return {}