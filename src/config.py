"""
项目配置模块
统一管理项目根目录路径，消除硬编码路径。
"""
import os

# 项目根目录 = 本文件的上上级目录(config.py在src/下)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 子目录
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

# 数据文件路径
HOTEL_INFO_PATH = os.path.join(DATA_DIR, 'hotel_info.csv')
CLEANED_PRICES_PATH = os.path.join(DATA_DIR, 'cleaned_hotel_prices.csv')
FUTURE_PRICES_PATH = os.path.join(DATA_DIR, 'hotel_future_prices.csv')


def work_dir():
    """向后兼容：返回项目根目录(替代旧的硬编码work_dir)"""
    return PROJECT_ROOT
