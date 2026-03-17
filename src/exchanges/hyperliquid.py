import time
import json
import requests
# import eth_account
# from eth_account.messages import encode_defunct
from exchanges.base import Exchange


class Hyper(Exchange):
    def __init__(self, api_key: str, api_secret: str):
        """
        api_key: 用户的钱包地址 (wallet address)
        api_secret: 用户的私钥 (private key)，用于签名
        """
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.hyperliquid.xyz"
        self.balance_total = 0.0

    def fetch_wallet_balance(self) -> dict:
        """获取现货资产余额"""
        endpoint = "/info"
        payload = {
            "type": "spotClearinghouseState",
            "user": self.api_key
        }
        response = self._make_request(endpoint, payload)

        # print(f"Hyperliquid Spot Response: {response}")

        balances = response.get("balances", [])
        non_zero = [b for b in balances if float(b.get("total", 0)) > 0]

        self.balance_total = sum(float(b.get("total", 0)) for b in non_zero)
        print(f"Hyperliquid Spot Total Balance (USDC): {self.balance_total}")
        # print(f"Hyperliquid Spot Balances: {non_zero}")

        return response

    def fetch_perp_balance(self) -> dict:
        """获取合约账户资产余额"""
        endpoint = "/info"
        payload = {
            "type": "clearinghouseState",
            "user": self.api_key
        }
        response = self._make_request(endpoint, payload)

        margin_summary = response.get("marginSummary", {})
        account_value = float(margin_summary.get("accountValue", 0))

        self.balance_total = account_value
        print(f"Hyperliquid Perp Account Value (USD): {self.balance_total}")
        print(f"Hyperliquid Perp Response: {response}")

        return response

    def _make_request(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}, Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            raise

    # def _generate_signature(self, params: dict) -> str:
    #     """使用私钥对消息进行签名（用于需要鉴权的操作）"""
    #     message = json.dumps(params, separators=(",", ":"))
    #     msg = encode_defunct(text=message)
    #     signed = eth_account.Account.sign_message(msg, private_key=self.api_secret)
    #     return signed.signature.hex()

    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)
