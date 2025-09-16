#!/usr/bin/env python3
"""
crypto_project_repository
- 统一获取加密项目的结构化数据（coin_data）并提供文本渲染（project_info）
- 内置进程级轻量缓存以减少重复外部请求

对外API：
- get_project_bundle(coin_id) -> { 'coin_data': dict, 'meta': {...} }
- render_project_info(coin_data: dict) -> str
"""

from __future__ import annotations

import time
from typing import Dict, Any

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

from tradingagents.dataflows.coingecko_utils import CoinGeckoAPI

_BUNDLE_CACHE: Dict[str, Dict[str, Any]] = {}
_BUNDLE_TTL_SECONDS: int = 120


def _now() -> float:
    return time.time()


def get_project_bundle(coin_id: str) -> Dict[str, Any]:
    """
    拉取并返回项目结构化数据包（带进程级缓存）。

    Returns:
        {
          'coin_data': dict,  # CoinGecko get_coin_info 原始结构化数据
          'meta': {
              'source': 'coingecko',
              'ts': <epoch_seconds>,
          }
        }
    """
    try:
        cache_entry = _BUNDLE_CACHE.get(coin_id)
        if cache_entry and (_now() - cache_entry.get('meta', {}).get('ts', 0) < _BUNDLE_TTL_SECONDS):
            return cache_entry

        api = CoinGeckoAPI()
        coin_data = api.get_coin_info(coin_id)

        bundle = {
            'coin_data': coin_data,
            'meta': {
                'source': 'coingecko',
                'ts': _now(),
            }
        }
        _BUNDLE_CACHE[coin_id] = bundle
        return bundle
    except Exception as e:
        logger.error(f"获取项目结构化数据失败: {e}")
        return {
            'coin_data': None,
            'meta': {'error': str(e), 'ts': _now()},
        }


def render_project_info(coin_data: Dict[str, Any]) -> str:
    """
    将结构化 coin_data 渲染为与现有 project_info 一致的文本格式。
    """
    try:
        if not isinstance(coin_data, dict):
            return "❌ 无法渲染项目信息：coin_data 非法或缺失"

        name = coin_data.get('name', 'Unknown')
        symbol = str(coin_data.get('symbol', '') or '').upper()

        homepage = ''
        links = coin_data.get('links')
        if isinstance(links, dict):
            hp = links.get('homepage')
            if isinstance(hp, list) and hp:
                homepage = hp[0]
            elif isinstance(hp, str):
                homepage = hp
        if not homepage:
            homepage = coin_data.get('homepage', '') or ''

        categories = coin_data.get('categories') or []
        if not isinstance(categories, list):
            categories = []

        market_data = coin_data.get('market_data') or {}

        def _usd(d: Any, key: str) -> float:
            if isinstance(d, dict) and isinstance(d.get(key), dict):
                return d.get(key, {}).get('usd', 0) or 0
            if isinstance(d, dict):
                return d.get(key, 0) or 0
            return 0

        current_price = _usd(market_data, 'current_price')
        market_cap = _usd(market_data, 'market_cap')
        total_volume = _usd(market_data, 'total_volume')

        desc = coin_data.get('description')
        if isinstance(desc, dict):
            description = desc.get('zh') or desc.get('en') or ''
        else:
            description = str(desc or '')

        report = f"""
🪙 加密货币详细信息: {name} ({symbol})

📊 基本信息:
- 名称: {name}
- 符号: {symbol}
- 官网: {homepage}
- 分类: {', '.join(categories[:5])}

💰 市场数据:
- 当前价格: ${current_price:,.2f}
- 市值: ${market_cap:,.0f}
- 24小时交易量: ${total_volume:,.0f}

📝 项目描述:
{description[:500]}{('...' if len(description) > 500 else '')}
"""
        return report
    except Exception as e:
        logger.error(f"渲染项目信息失败: {e}")
        return f"❌ 渲染项目信息失败: {str(e)}"


