import os
import sys
from exchanges.bybit import Bybit

# 将 src 目录添加到模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

bybit = Bybit(api_key=os.getenv('BYBIT_API_KEY'), api_secret=os.getenv('BYBIT_API_SECRET'))

bybit.get_position_list(category="option")
