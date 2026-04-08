import hmac
import hashlib
import time
import urllib.parse
import requests
import json
import uuid

from .base import Exchange


class Bybit(Exchange):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret)
        self.base_url = "https://api.bybit.com"
        self.balance_total = 0.0

    def fetch_wallet_balance(self, account_type: str = "UNIFIED") -> dict:
        endpoint = "/v5/account/wallet-balance"
        params = {
            "accountType": account_type,
        }
        headers, params = self._build_signed_headers(params)
        response = self._make_request("GET", endpoint, headers=headers, params=params)
        print(f"fetch_wallet_balance Bybit API Response: {response}")

        return response

    def fetch_asset_overview(self) -> dict:
        endpoint = "/v5/asset/asset-overview"
        params = {}
        headers, params = self._build_signed_headers(params)
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

        headers, params = self._build_signed_headers(params)
        response = self._make_request("GET", endpoint, headers=headers, params=params)
        # print(f"get_position_list Bybit API Response: {response}")

        return response

    def create_order(
        self,
        category: str,
        symbol: str,
        side: str,
        orderType: str,
        qty: str,
        price: str = None,
        timeInForce: str = None,
        orderLinkId: str = None,
        reduceOnly: bool = None,
        closeOnTrigger: bool = None,
        iv: str = None,
    ) -> dict:
        """
        下单 POST /v5/order/create

        :param category: 产品类型 linear/inverse/option/spot (必填)
        :param symbol: 交易对名称, 例如 BTC-29NOV24-80000-C (必填)
        :param side: 方向 Buy/Sell (必填)
        :param orderType: 订单类型 Market/Limit (必填)
        :param qty: 下单数量 (必填)
        :param price: 限价单价格, Market 单可不填 (可选)
        :param timeInForce: 执行策略 GTC/IOC/FOK, 默认 GTC (可选)
        :param orderLinkId: 自定义订单 ID (可选)
        :param reduceOnly: 是否只减仓, 适用于 linear/inverse (可选)
        :param closeOnTrigger: 触发后是否平仓 (可选)
        :param iv: 隐含波动率, 仅 option 限价单有效 (可选)
        :return: 下单结果字典
        """
        endpoint = "/v5/order/create"
        params = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": orderType,
            "timeInForce": timeInForce if timeInForce is not None else "GTC",
            "qty": qty,
            "orderLinkId": orderLinkId if orderLinkId is not None else str(uuid.uuid4())
        }

        if price is not None:
            params["price"] = price
        if reduceOnly is not None:
            params["reduceOnly"] = reduceOnly
        if closeOnTrigger is not None:
            params["closeOnTrigger"] = closeOnTrigger
        if iv is not None:
            params["iv"] = iv

        headers, body = self._build_signed_headers(params, is_post=True)
        response = self._make_request("POST", endpoint, headers=headers, body=body)

        # print(f"create_order Bybit API Response: {response}")

        return response


    def get_kline(
        self,
        symbol: str,
        interval: str,
        start: int = None,
        end: int = None,
        limit: int = 200,
    ) -> list:
        """
        获取 K 线数据 GET /v5/market/kline (公开接口，无需签名)

        :param symbol: 交易对，例如 ETHUSDT
        :param interval: K 线周期，例如 D (日线), 60 (小时线)
        :param start: 开始时间戳（毫秒，可选）
        :param end: 结束时间戳（毫秒，可选）
        :param limit: 返回数量，最大 200，默认 200
        :return: K 线列表，每条 [startTime, open, high, low, close, volume, turnover]
        """
        endpoint = "/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end

        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"get_kline Request Error: {e}")
            raise

        result = data.get("result", {})
        return result.get("list", [])

    def _make_request(self, method, endpoint, headers, params=None, body=None):
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "POST" and body is not None:
                # 手动序列化，确保无空格，与签名一致
                raw_body = json.dumps(body, separators=(',', ':'))
                response = requests.request(method, url, headers=headers, data=raw_body)
            else:
                response = requests.request(method, url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}, Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            raise

    def _generate_signature(self, timestamp: int, recv_window: str, params: dict, is_post: bool = False) -> str:
        if is_post:
            # POST 请求使用 JSON 字符串，且不能有空格
            param_str = f"{timestamp}{self.api_key}{recv_window}{json.dumps(params, separators=(',', ':'))}"
        else:
            # GET 请求使用 query string
            query_string = urllib.parse.urlencode(params)
            param_str = f"{timestamp}{self.api_key}{recv_window}{query_string}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _get_timestamp(self):
        return int(time.time() * 1000)
    
    def _build_signed_headers(self, params: dict = None, recv_window: str = "5000", is_post: bool = False) -> tuple[dict, dict]:
        """
        构建带签名的请求头和参数。
        返回 (headers, params)
        """
        if params is None:
            params = {}
        timestamp = self._get_timestamp()
        signature = self._generate_signature(timestamp, recv_window, params, is_post=is_post)
        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }
        return headers, params