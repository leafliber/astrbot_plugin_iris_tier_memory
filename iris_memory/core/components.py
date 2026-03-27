"""
Iris Tier Memory - 组件初始化框架

提供统一的组件生命周期管理，支持：
- 抽象基类定义
- 细粒度状态追踪
- 独立初始化与故障隔离
- 异步生命周期管理
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
import asyncio

from .logger import get_logger

logger = get_logger("components")


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class SystemStatus:
    """系统各模块可用性状态
    
    细粒度追踪各层功能模块的可用性，替代单一布尔值，
    便于上层逻辑根据实际状态灵活降级。
    
    使用字典集中管理模块可用性，由 ComponentManager 动态注册。
    
    Attributes:
        _availability: 模块可用性字典 {module_name: bool}
    
    Examples:
        >>> status = SystemStatus()
        >>> status.register_module("l2_memory", False)
        >>> status.set_available("l2_memory")
        >>> status.get_available_modules()
        ['l2_memory']
        >>> status.is_module_available("l2_memory")
        True
    """
    
    _availability: Dict[str, bool] = field(default_factory=dict)
    
    def register_module(self, module_name: str, default_available: bool = False) -> None:
        """注册模块
        
        Args:
            module_name: 模块名称
            default_available: 默认是否可用
        """
        self._availability[module_name] = default_available
    
    def set_available(self, module_name: str, available: bool = True) -> None:
        """设置模块可用性
        
        Args:
            module_name: 模块名称
            available: 是否可用
        """
        if module_name in self._availability:
            self._availability[module_name] = available
    
    def is_module_available(self, module_name: str) -> bool:
        """检查指定模块是否可用
        
        Args:
            module_name: 模块名称
        
        Returns:
            模块是否可用
        
        Examples:
            >>> status.is_module_available("l2")
            False
            >>> status.is_module_available("l1")
            True
        """
        return self._availability.get(module_name, False)
    
    def get_available_modules(self) -> List[str]:
        """获取可用模块名称列表
        
        Returns:
            可用模块的名称列表
        
        Examples:
            >>> status.get_available_modules()
            ['l1']
        """
        return [m for m, available in self._availability.items() if available]
    
    def get_unavailable_modules(self) -> List[str]:
        """获取不可用模块名称列表
        
        Returns:
            不可用模块的名称列表
        
        Examples:
            >>> status.get_unavailable_modules()
            ['l2', 'l3', 'profile', 'scheduler', 'image_quota']
        """
        return [m for m, available in self._availability.items() if not available]
    
    def to_dict(self) -> Dict[str, bool]:
        """转换为字典
        
        Returns:
            状态字典 {module_name_available: bool}
        """
        return {f"{m}_available": available for m, available in self._availability.items()}


@dataclass
class ComponentInitResult:
    """组件初始化结果
    
    记录单个组件的初始化状态，用于日志追踪和状态汇总。
    
    Attributes:
        name: 组件名称
        success: 是否成功
        error_message: 错误信息（失败时）
    
    Examples:
        >>> result = ComponentInitResult("chromadb", True)
        >>> result.success
        True
    """
    
    name: str
    success: bool
    error_message: Optional[str] = None


# ============================================================================
# 抽象基类
# ============================================================================

class Component(ABC):
    """组件抽象基类
    
    所有组件（ChromaDB、KuzuDB、画像存储等）需继承此类，
    实现统一的初始化和关闭接口。
    
    Attributes:
        _is_available: 组件是否可用
        _init_error: 初始化错误信息
    
    Examples:
        >>> class ChromaDBComponent(Component):
        ...     @property
        ...     def name(self) -> str:
        ...         return "chromadb"
        ...     
        ...     async def initialize(self) -> None:
        ...         self._is_available = True
        ...     
        ...     async def shutdown(self) -> None:
        ...         self._is_available = False
    """
    
    def __init__(self):
        self._is_available: bool = False
        self._init_error: Optional[str] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """组件名称，用于日志标识
        
        Returns:
            组件名称字符串
        """
        pass
    
    @property
    def is_available(self) -> bool:
        """组件是否可用
        
        Returns:
            可用状态
        """
        return self._is_available
    
    @property
    def init_error(self) -> Optional[str]:
        """初始化错误信息
        
        Returns:
            错误信息字符串，无错误时为 None
        """
        return self._init_error
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化组件
        
        子类需实现此方法，完成资源初始化（如数据库连接、文件创建等）。
        成功时设置 `_is_available = True`，失败时设置 `_init_error`。
        
        Raises:
            Exception: 初始化失败时抛出异常，由 ComponentManager 捕获
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭组件
        
        子类需实现此方法，完成资源释放（如关闭连接、保存状态等）。
        """
        pass


# ============================================================================
# 组件管理器
# ============================================================================

class ComponentManager:
    """组件生命周期管理器
    
    负责协调多个组件的初始化和关闭，提供故障隔离和状态追踪。
    
    Features:
        - 独立初始化：单组件失败不影响其他组件
        - 状态追踪：细粒度追踪各层可用性
        - 线程安全：使用 asyncio.Lock 保护关键操作
        - 组件查询：按名称或可用性获取组件
    
    Attributes:
        _components: 组件元组（不可变）
        _initialized: 是否已初始化
        _lock: 异步锁
        _status: 系统状态
    
    Examples:
        >>> from iris_memory.storage import ChromaAdapter, KuzuAdapter
        >>> 
        >>> components = (ChromaAdapter(), KuzuAdapter())
        >>> manager = ComponentManager(components)
        >>> 
        >>> # 初始化所有组件
        >>> results = await manager.initialize_all()
        >>> 
        >>> # 查询状态
        >>> status = manager.status
        >>> print(status.to_dict())
    """
    
    def __init__(self, components: Tuple[Component, ...]):
        """初始化组件管理器
        
        Args:
            components: 组件元组，按初始化顺序排列
        """
        self._components = components
        self._initialized = False
        self._lock = asyncio.Lock()
        self._status = SystemStatus()
        
        # 动态注册模块
        for component in components:
            self._status.register_module(component.name, default_available=False)
        
        logger.info(f"组件管理器已创建，共 {len(components)} 个组件，已注册模块：{list(self._status._availability.keys())}")
    
    @property
    def status(self) -> SystemStatus:
        """获取系统状态
        
        Returns:
            系统状态对象
        """
        return self._status
    
    async def initialize_all(self) -> List[ComponentInitResult]:
        """初始化所有组件
        
        按组件在元组中的顺序依次初始化，单组件失败不影响其他组件。
        初始化完成后更新系统状态。
        
        Returns:
            初始化结果列表
        
        Raises:
            RuntimeError: 已初始化时抛出
        
        Notes:
            - 使用 asyncio.Lock 保护初始化过程
            - 每个组件的初始化错误会被捕获并记录
        """
        async with self._lock:
            if self._initialized:
                raise RuntimeError("组件已初始化，请勿重复调用")
            
            logger.info("开始初始化组件...")
            results: List[ComponentInitResult] = []
            
            for component in self._components:
                result = await self._init_single_component(component)
                results.append(result)
            
            # 更新系统状态
            self._update_status()
            self._initialized = True
            
            # 统计结果
            success_count = sum(1 for r in results if r.success)
            logger.info(
                f"组件初始化完成：{success_count}/{len(results)} 成功，"
                f"可用模块：{', '.join(self._status.get_available_modules())}"
            )
            
            return results
    
    async def _init_single_component(self, component: Component) -> ComponentInitResult:
        """初始化单个组件
        
        Args:
            component: 组件实例
        
        Returns:
            初始化结果
        """
        try:
            logger.debug(f"正在初始化组件：{component.name}")
            await component.initialize()
            
            if component.is_available:
                logger.info(f"组件 {component.name} 初始化成功")
                return ComponentInitResult(component.name, True)
            else:
                error_msg = component.init_error or "初始化后组件不可用"
                logger.warning(f"组件 {component.name} 初始化失败：{error_msg}")
                return ComponentInitResult(component.name, False, error_msg)
        
        except Exception as e:
            error_msg = str(e)
            component._init_error = error_msg
            logger.error(f"组件 {component.name} 初始化异常：{error_msg}", exc_info=True)
            return ComponentInitResult(component.name, False, error_msg)
    
    def _update_status(self) -> None:
        """更新系统状态
        
        根据各组件的可用性更新 SystemStatus。
        """
        # 重置为默认状态
        self._status = SystemStatus()
        for component in self._components:
            self._status.register_module(component.name, default_available=False)
        
        # 更新可用组件
        for component in self._components:
            if component.is_available:
                self._status.set_available(component.name, True)
    
    async def shutdown_all(self) -> None:
        """关闭所有组件
        
        按组件在元组中的逆序依次关闭。
        即使部分组件关闭失败，也会继续关闭其他组件。
        
        Notes:
            - 使用 asyncio.Lock 保护关闭过程
            - 关闭后重置初始化状态
        """
        async with self._lock:
            if not self._initialized:
                logger.debug("组件未初始化，无需关闭")
                return
            
            logger.info("开始关闭组件...")
            
            # 逆序关闭组件
            for component in reversed(self._components):
                try:
                    logger.debug(f"正在关闭组件：{component.name}")
                    await component.shutdown()
                    logger.info(f"组件 {component.name} 已关闭")
                except Exception as e:
                    logger.error(f"组件 {component.name} 关闭失败：{e}", exc_info=True)
            
            # 重置状态
            self._status = SystemStatus()
            for component in self._components:
                self._status.register_module(component.name, default_available=False)
            self._initialized = False
            
            logger.info("所有组件已关闭")
    
    def get_component(self, name: str) -> Optional[Component]:
        """按名称获取组件
        
        Args:
            name: 组件名称
        
        Returns:
            组件实例，找不到时返回 None
        """
        for component in self._components:
            if component.name == name:
                return component
        return None
    
    def get_available_components(self) -> List[Component]:
        """获取所有可用组件
        
        Returns:
            可用组件列表
        """
        return [c for c in self._components if c.is_available]
    
    def get_failed_components(self) -> List[Component]:
        """获取所有失败的组件
        
        Returns:
            失败组件列表
        """
        return [c for c in self._components if not c.is_available]
