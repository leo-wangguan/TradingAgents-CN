#!/usr/bin/env python3
"""
加密货币缓存管理器
专门管理加密货币数据的缓存，包括价格、项目信息、新闻等
"""

import os
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()


class CryptoDataCache:
    """
    加密货币数据缓存管理器
    专门处理加密货币相关的数据缓存
    """

    def __init__(self, cache_dir: str = None):
        """
        初始化加密货币缓存管理器
        
        Args:
            cache_dir: 缓存目录路径
        """
        # 设置缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # 默认缓存目录
            default_cache_dir = os.path.join(
                os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
                "data_cache"
            )
            self.cache_dir = Path(default_cache_dir)
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        subdirs = ['crypto_market', 'crypto_info', 'crypto_news', 'crypto_search']
        for subdir in subdirs:
            (self.cache_dir / subdir).mkdir(exist_ok=True)

        # 加密货币缓存配置
        self.cache_config = {
            'crypto_market_data': {
                'ttl_hours': 1,  # 加密货币市场数据缓存1小时（实时性要求高）
                'max_files': 500,
                'description': '加密货币市场数据'
            },
            'crypto_info': {
                'ttl_hours': 24,  # 加密货币项目信息缓存24小时
                'max_files': 200,
                'description': '加密货币项目信息'
            },
            'crypto_news': {
                'ttl_hours': 6,  # 加密货币新闻缓存6小时
                'max_files': 300,
                'description': '加密货币新闻数据'
            },
            'crypto_search': {
                'ttl_hours': 12,  # 加密货币搜索结果缓存12小时
                'max_files': 100,
                'description': '加密货币搜索结果'
            }
        }

        logger.info(f"🪙 加密货币缓存管理器初始化完成，缓存目录: {self.cache_dir}")
        logger.info(f"   市场数据: ✅ 已配置")
        logger.info(f"   项目信息: ✅ 已配置")
        logger.info(f"   新闻数据: ✅ 已配置")
        logger.info(f"   搜索结果: ✅ 已配置")

    def _determine_crypto_type(self, coin_id: str) -> str:
        """根据加密货币ID确定缓存类型"""
        # 这里可以根据需要添加更复杂的逻辑
        # 目前简单返回通用类型
        return 'crypto'

    def _generate_cache_key(self, data_type: str, coin_id: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            data_type: 数据类型
            coin_id: 加密货币ID
            **kwargs: 其他参数
            
        Returns:
            str: 缓存键
        """
        # 构建缓存键
        key_parts = [data_type, coin_id]
        
        # 添加其他参数
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}_{value}")
        
        return "_".join(key_parts)

    def _get_cache_file_path(self, cache_key: str, data_type: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            cache_key: 缓存键
            data_type: 数据类型
            
        Returns:
            Path: 缓存文件路径
        """
        # 根据数据类型选择子目录
        subdir_map = {
            'market': 'crypto_market',
            'info': 'crypto_info',
            'news': 'crypto_news',
            'search': 'crypto_search'
        }
        
        subdir = subdir_map.get(data_type, 'crypto_market')
        filename = f"{cache_key}.json"
        
        return self.cache_dir / subdir / filename

    def get_cached_data(self, data_type: str, coin_id: str, **kwargs) -> Optional[Dict]:
        """
        获取缓存数据
        
        Args:
            data_type: 数据类型
            coin_id: 加密货币ID
            **kwargs: 其他参数
            
        Returns:
            Optional[Dict]: 缓存数据，如果不存在或过期则返回None
        """
        try:
            cache_key = self._generate_cache_key(data_type, coin_id, **kwargs)
            cache_file = self._get_cache_file_path(cache_key, data_type)
            
            if not cache_file.exists():
                return None
            
            # 检查文件是否过期
            config = self.cache_config.get(f'crypto_{data_type}', self.cache_config['crypto_market_data'])
            ttl_seconds = config['ttl_hours'] * 3600
            
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age > ttl_seconds:
                logger.debug(f"🪙 缓存已过期: {cache_file}")
                cache_file.unlink()  # 删除过期文件
                return None
            
            # 读取缓存数据
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"🪙 缓存命中: {cache_file}")
            return data
            
        except Exception as e:
            logger.error(f"❌ 读取缓存失败: {e}")
            return None

    def set_cached_data(self, data_type: str, coin_id: str, data: Dict, **kwargs) -> bool:
        """
        设置缓存数据
        
        Args:
            data_type: 数据类型
            coin_id: 加密货币ID
            data: 要缓存的数据
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功
        """
        try:
            cache_key = self._generate_cache_key(data_type, coin_id, **kwargs)
            cache_file = self._get_cache_file_path(cache_key, data_type)
            
            # 确保目录存在
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入缓存数据
            import json
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"🪙 缓存已保存: {cache_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存缓存失败: {e}")
            return False

    def clear_expired_cache(self) -> int:
        """
        清理过期缓存
        
        Returns:
            int: 清理的文件数量
        """
        cleaned_count = 0
        
        try:
            for subdir in ['crypto_market', 'crypto_info', 'crypto_news', 'crypto_search']:
                subdir_path = self.cache_dir / subdir
                if not subdir_path.exists():
                    continue
                
                # 获取对应的配置
                data_type = subdir.replace('crypto_', '')
                config = self.cache_config.get(f'crypto_{data_type}', self.cache_config['crypto_market_data'])
                ttl_seconds = config['ttl_hours'] * 3600
                
                # 检查每个文件
                for cache_file in subdir_path.glob('*.json'):
                    try:
                        file_age = time.time() - cache_file.stat().st_mtime
                        if file_age > ttl_seconds:
                            cache_file.unlink()
                            cleaned_count += 1
                            logger.debug(f"🪙 清理过期缓存: {cache_file}")
                    except Exception as e:
                        logger.error(f"❌ 清理缓存文件失败 {cache_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"🪙 清理了 {cleaned_count} 个过期缓存文件")
            
        except Exception as e:
            logger.error(f"❌ 清理缓存失败: {e}")
        
        return cleaned_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_type': {}
        }
        
        try:
            for subdir in ['crypto_market', 'crypto_info', 'crypto_news', 'crypto_search']:
                subdir_path = self.cache_dir / subdir
                if not subdir_path.exists():
                    continue
                
                type_stats = {
                    'files': 0,
                    'size': 0
                }
                
                for cache_file in subdir_path.glob('*.json'):
                    try:
                        type_stats['files'] += 1
                        type_stats['size'] += cache_file.stat().st_size
                    except Exception as e:
                        logger.error(f"❌ 统计缓存文件失败 {cache_file}: {e}")
                
                stats['by_type'][subdir] = type_stats
                stats['total_files'] += type_stats['files']
                stats['total_size'] += type_stats['size']
            
        except Exception as e:
            logger.error(f"❌ 获取缓存统计失败: {e}")
        
        return stats


# 全局加密货币缓存管理器实例
_crypto_cache_manager = None

def get_crypto_cache_manager() -> CryptoDataCache:
    """获取全局加密货币缓存管理器实例"""
    global _crypto_cache_manager
    if _crypto_cache_manager is None:
        _crypto_cache_manager = CryptoDataCache()
    return _crypto_cache_manager
