"""
Iris Tier Memory - 隐藏配置管理器

管理隐藏配置的存储、修改和持久化，提供：
- 内存缓存 + 文件持久化
- 线程安全(RLock)
- 观察者模式支持
- 热修改支持
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import asdict

from .defaults import HiddenConfig


logger = logging.getLogger("astrbot")


class HiddenConfigManager:
    """隐藏配置管理器
    
    特性：
    - 内存缓存：避免频繁文件读取
    - 文件持久化：运行时自动保存到 data/iris_memory/hidden_config.json
    - 线程安全：使用 RLock 保护读写操作
    - 观察者模式：配置变更时通知订阅者
    - 热修改支持：运行时通过 set() 方法修改配置
    
    风险说明：
    - 当用户配置与隐藏配置同时存在时，优先使用用户配置(在 Config 类中处理)
    - 热修改后立即生效，但可能导致其他模块的缓存不一致，需通过观察者模式处理
    """
    
    def __init__(self, config_path: Path, defaults: HiddenConfig):
        """初始化隐藏配置管理器
        
        Args:
            config_path: 配置文件路径(data/iris_memory/hidden_config.json)
            defaults: 默认配置对象
        """
        self._path = config_path
        self._defaults = defaults
        self._cache: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._observers: List[Callable[[str, Any, Any], None]] = []
        
        # 确保目录存在
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._load()
    
    def _load(self) -> None:
        """从文件加载隐藏配置到缓存"""
        with self._lock:
            if not self._path.exists():
                # 文件不存在，使用默认值
                logger.debug(f"[iris-memory:config] 隐藏配置文件不存在，使用默认值: {self._path}")
                return
            
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    self._cache = data
                    logger.info(f"[iris-memory:config] 成功加载隐藏配置，共 {len(self._cache)} 项")
                else:
                    logger.warning(f"[iris-memory:config] 隐藏配置文件格式错误，使用默认值")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"[iris-memory:config] 隐藏配置文件损坏，使用默认值: {e}")
            except Exception as e:
                logger.error(f"[iris-memory:config] 加载隐藏配置失败: {e}")
    
    def _persist(self) -> None:
        """持久化隐藏配置到文件"""
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"[iris-memory:config] 隐藏配置已持久化到 {self._path}")
        except Exception as e:
            logger.error(f"[iris-memory:config] 持久化隐藏配置失败: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取隐藏配置值
        
        Args:
            key: 配置键名(如 "debug_mode")
        
        Returns:
            配置值，找不到返回 None
        
        优先级：
            1. 缓存中的值
            2. 默认值
        """
        with self._lock:
            # 优先从缓存获取
            if key in self._cache:
                return self._cache[key]
            
            # 返回默认值
            return getattr(self._defaults, key, None)
    
    def set(self, key: str, value: Any) -> None:
        """设置隐藏配置(热修改)
        
        Args:
            key: 配置键名
            value: 配置值
        
        特性：
            - 线程安全
            - 自动持久化
            - 通知观察者
            - 记录日志
        
        风险说明：
            - 如果用户在 WebUI 中也设置了同名配置，优先使用用户配置
            - 热修改可能导致其他模块的缓存不一致，需通过观察者模式处理
        """
        with self._lock:
            old_value = self._cache.get(key)
            
            # 更新缓存
            self._cache[key] = value
            
            # 持久化
            self._persist()
            
            # 记录日志
            logger.info(f"[iris-memory:config] 隐藏配置已修改: {key} = {value} (原值: {old_value})")
            
            # 通知观察者
            for observer in self._observers:
                try:
                    observer(key, old_value, value)
                except Exception as e:
                    logger.error(f"[iris-memory:config] 观察者回调执行失败: {e}")
    
    def update(self, updates: Dict[str, Any]) -> None:
        """批量更新隐藏配置
        
        Args:
            updates: 配置字典 {key: value}
        
        特性：
            - 批量更新时只持久化一次
            - 每个配置项都会触发观察者回调
        """
        with self._lock:
            for key, value in updates.items():
                old_value = self._cache.get(key)
                self._cache[key] = value
                
                # 通知观察者
                for observer in self._observers:
                    try:
                        observer(key, old_value, value)
                    except Exception as e:
                        logger.error(f"[iris-memory:config] 观察者回调执行失败: {e}")
            
            # 统一持久化
            self._persist()
            logger.info(f"[iris-memory:config] 批量更新隐藏配置，共 {len(updates)} 项")
    
    def delete(self, key: str) -> bool:
        """删除隐藏配置项
        
        Args:
            key: 配置键名
        
        Returns:
            是否删除成功(键不存在返回 False)
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            old_value = self._cache.pop(key)
            self._persist()
            
            logger.info(f"[iris-memory:config] 已删除隐藏配置: {key} (原值: {old_value})")
            
            # 通知观察者(新值为 None 表示已删除)
            for observer in self._observers:
                try:
                    observer(key, old_value, None)
                except Exception as e:
                    logger.error(f"[iris-memory:config] 观察者回调执行失败: {e}")
            
            return True
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有隐藏配置(缓存 + 默认值)
        
        Returns:
            配置字典
        """
        with self._lock:
            # 从默认值开始
            result = asdict(self._defaults)
            # 用缓存覆盖
            result.update(self._cache)
            return result
    
    def add_observer(self, callback: Callable[[str, Any, Any], None]) -> None:
        """添加配置变更观察者
        
        Args:
            callback: 回调函数，签名为 (key, old_value, new_value) -> None
        
        Examples:
            >>> def on_config_change(key: str, old_value: Any, new_value: Any):
            ...     logger.info(f"配置 {key} 已修改: {old_value} -> {new_value}")
            >>> manager.add_observer(on_config_change)
        """
        with self._lock:
            self._observers.append(callback)
            logger.debug(f"[iris-memory:config] 已添加配置变更观察者，当前共 {len(self._observers)} 个")
    
    def remove_observer(self, callback: Callable[[str, Any, Any], None]) -> bool:
        """移除配置变更观察者
        
        Args:
            callback: 回调函数
        
        Returns:
            是否移除成功
        """
        with self._lock:
            try:
                self._observers.remove(callback)
                logger.debug(f"[iris-memory:config] 已移除配置变更观察者，当前共 {len(self._observers)} 个")
                return True
            except ValueError:
                return False
    
    def clear_cache(self) -> None:
        """清空缓存(保留持久化文件)"""
        with self._lock:
            self._cache.clear()
            logger.info("[iris-memory:config] 已清空隐藏配置缓存")
    
    def reset_to_defaults(self) -> None:
        """重置为默认值"""
        with self._lock:
            self._cache.clear()
            self._persist()
            logger.info("[iris-memory:config] 已重置隐藏配置为默认值")
