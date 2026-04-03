import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

# 加载 .env 文件中的环境变量
load_dotenv()

session = HTTP(
    testnet=False,  # 使用真实环境，测试网设为True
    api_key=os.getenv('BYBIT_API_KEY'),
    api_secret=os.getenv('BYBIT_API_SECRET'),
)

def get_account_balance():
    """获取账户资产"""
    try:
        # 获取统一账户余额 (UNIFIED账户)
        response = session.get_wallet_balance(
            accountType="UNIFIED",  # 账户类型: UNIFIED, CONTRACT, SPOT
        )
        if response["retCode"] == 0:
            account_list = response["result"]["list"]
            for account in account_list:
                print(f"账户类型: {account['accountType']}")
                print(f"总权益(USD): {account['totalEquity']}")
                print(f"总可用余额(USD): {account['totalAvailableBalance']}")
                print(f"未实现盈亏(USD): {account['totalPerpUPL']}")
                print("\n各币种余额:")
                # for coin in account["coin"]:
                #     if float(coin["walletBalance"]) > 0:
                #         print(f"  币种: {coin['coin']}")
                #         print(f"    钱包余额: {coin['walletBalance']}")
                #         print(f"    可用余额: {coin['availableToWithdraw']}")
                #         print(f"    未实现盈亏: {coin['unrealisedPnl']}")
        else:
            print(f"获取余额失败: {response['retMsg']}")
    except Exception as e:
        print(f"发生错误: {e}")


def get_option_positions():
    """获取期权仓位"""
    try:
        # 获取期权仓位
        response = session.get_positions(
            category="option",   # 期权类型
            # symbol="BTC-29DEC23-40000-C",  # 可指定具体期权合约，不填则获取所有
            settleCoin="USDT",   # 结算币种，期权通常为USDC
        )
        if response["retCode"] == 0:
            positions = response["result"]["list"]
            if not positions:
                print("当前没有期权仓位")
                return
            print(f"共有 {len(positions)} 个期权仓位:")
            for pos in positions:
                print(f"\n合约: {pos['symbol']}")
                print(f"  方向: {pos['side']}")
                print(f"  持仓数量: {pos['size']}")
                print(f"  均价: {pos['avgPrice']}")
                print(f"  标记价格: {pos['markPrice']}")
                print(f"  未实现盈亏: {pos['unrealisedPnl']}")
                print(f"  已实现盈亏: {pos['cumRealisedPnl']}")
                print(f"  Delta: {pos.get('delta', 'N/A')}")
                print(f"  Gamma: {pos.get('gamma', 'N/A')}")
                print(f"  Theta: {pos.get('theta', 'N/A')}")
                print(f"  Vega: {pos.get('vega', 'N/A')}")
        else:
            print(f"获取期权仓位失败: {response['retMsg']}")
    except Exception as e:
        print(f"发生错误: {e}")


def get_option_Greeks():
    """获取账户整体期权Greeks"""
    try:
        response = session.get_fee_rates(
            category="option",
        )
        # 获取期权账户Greeks汇总
        response = session.get_account_info()
        if response["retCode"] == 0:
            print("账户信息:")
            print(response["result"])
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("获取账户资产")
    print("=" * 50)
    get_account_balance()

    print("\n" + "=" * 50)
    print("获取期权仓位")
    print("=" * 50)
    get_option_positions()