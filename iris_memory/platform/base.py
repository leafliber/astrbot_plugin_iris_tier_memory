"""
Iris Tier Memory - 平台适配器抽象基类

定义平台适配器的统一接口，用于屏蔽不同消息平台（QQ、微信等）的差异。

设计原则：
- 无状态适配器：每次调用传入事件对象，避免生命周期问题
- 统一异常处理：定义平台相关的异常类型
- 平台无关接口：上层模块通过抽象接口访问平台信息
"""

from abc import ABC, abstractmethod


class UnsupportedPlatformError(Exception):
    """不支持的平台类型异常
    
    当遇到未实现的平台适配器类型时抛出。
    
    Examples:
        >>> raise UnsupportedPlatformError("ge微信", "当前仅支持 QQ 平台")
    """
    
    def __init__(self, platform_type: str, message: str = ""):
        self.platform_type = platform_type
        self.message = message or f"不支持的平台类型: {platform_type}"
        super().__init__(self.message)


class PlatformAdapter(ABC):
    """平台适配器抽象基类
    
    定义统一的平台信息访问接口，用于获取用户ID、群ID等平台相关信息。
    各平台适配器（如 OneBot11Adapter）需要实现具体逻辑。
    
    设计要点：
    - 无状态设计：不持有事件引用，每次调用传入事件对象
    - 线程安全：无实例状态，所有方法可安全并发调用
    - 平台无关：上层模块通过抽象接口访问，不依赖具体平台
    
    Examples:
        >>> from iris_memory.platform import get_adapter
        >>> 
        >>> adapter = get_adapter(event)
        >>> user_id = adapter.get_user_id(event)
        >>> group_id = adapter.get_group_id(event)
    """
    
    @abstractmethod
    def get_user_id(self, event: "AstrMessageEvent") -> str:
        """获取用户ID（平台原始ID）
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            用户ID字符串
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> user_id = adapter.get_user_id(event)  # "123456789"
        """
        pass
    
    @abstractmethod
    def get_user_name(self, event: "AstrMessageEvent") -> str:
        """获取用户显示名称
        
        在群聊场景下，优先返回群名片（如果有），否则返回昵称。
        在私聊场景下，直接返回用户昵称。
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            用户显示名称字符串
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> name = adapter.get_user_name(event)  # "张三" 或群名片
        """
        pass
    
    @abstractmethod
    def get_user_nickname(self, event: "AstrMessageEvent") -> str:
        """获取用户原始昵称
        
        不考虑群名片，始终返回用户的原始昵称。
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            用户昵称字符串
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> nickname = adapter.get_user_nickname(event)  # "张三"
        """
        pass
    
    @abstractmethod
    def get_group_id(self, event: "AstrMessageEvent") -> str:
        """获取群聊ID
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            群聊ID字符串，私聊时返回空字符串 ""
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> group_id = adapter.get_group_id(event)  # "987654321" 或 ""
        """
        pass
    
    @abstractmethod
    def get_group_name(self, event: "AstrMessageEvent") -> str:
        """获取群聊名称
        
        从原始消息中提取群名称信息（如果可用）。
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            群聊名称字符串，无法获取时返回空字符串 ""
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> group_name = adapter.get_group_name(event)  # "技术交流群" 或 ""
        """
        pass
    
    @abstractmethod
    def get_user_role(self, event: "AstrMessageEvent") -> str:
        """获取用户在群聊中的角色
        
        常见角色：owner(群主)、admin(管理员)、member(普通成员)。
        私聊时返回 "private"。
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            角色字符串：owner、admin、member、private
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> role = adapter.get_user_role(event)  # "admin"
        """
        pass
    
    @abstractmethod
    def get_raw_message(self, event: "AstrMessageEvent") -> dict[str, object]:
        """获取平台原始消息对象
        
        返回消息平台适配器的原始消息对象（转为字典），
        用于访问平台特定的高级信息。
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            原始消息字典，解析失败时返回空字典 {}
        
        Raises:
            AttributeError: event 结构不符合预期
        
        Examples:
            >>> raw = adapter.get_raw_message(event)
            >>> print(raw.get("user_id"))  # 平台特定字段
        
        Notes:
            - 不同平台的原始消息结构不同，需查阅平台文档
            - OneBot11 原始消息结构参考：https://github.com/botuniverse/onebot-11
        """
        pass
    
    @abstractmethod
    def is_group_message(self, event: "AstrMessageEvent") -> bool:
        """判断是否为群聊消息
        
        通过群ID是否为空来判断消息类型。
        
        Args:
            event: AstrBot 消息事件对象 (AstrMessageEvent)
        
        Returns:
            True 表示群聊消息，False 表示私聊消息
        
        Examples:
            >>> if adapter.is_group_message(event):
            ...     print("这是群聊消息")
        """
        pass
