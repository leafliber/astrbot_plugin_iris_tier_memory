"""
Iris Tier Memory - 默认配置定义

使用 dataclass 提供类型安全的配置定义，支持：
- IDE 自动补全
- 编译时类型检查
- 字段注释即文档
- 扁平化键名访问
"""

from dataclasses import dataclass, field, asdict
from typing import Literal, Optional, Dict


@dataclass
class L1BufferConfig:
    """L1 消息上下文缓冲配置"""
    enable: bool = True
    summary_provider: str = ""
    inject_queue_length: int = 20
    max_queue_tokens: int = 4000
    max_single_message_tokens: int = 500


@dataclass
class L2MemoryConfig:
    """L2 记忆库配置"""
    enable: bool = True
    summary_provider: str = ""
    enable_graph_enhancement: bool = False
    top_k: int = 10
    max_entries: int = 10000
    timeout_ms: int = 2000


@dataclass
class L3KGConfig:
    """L3 知识图谱配置"""
    enable: bool = True
    max_nodes: int = 50000
    max_edges: int = 100000
    timeout_ms: int = 1500
    expansion_depth: int = 2
    enable_type_whitelist: bool = True


@dataclass
class ImageParsingConfig:
    """图片解析配置"""
    enable: bool = False
    provider: str = ""
    parsing_mode: Literal["all", "related"] = "related"
    daily_quota: int = 200


@dataclass
class ProfileConfig:
    """画像系统配置"""
    enable: bool = True
    analysis_mode: Literal["all", "related"] = "all"


@dataclass
class EnhancementConfig:
    """记忆增强配置"""
    enable_rerank: bool = False
    rerank_provider: str = ""


@dataclass
class IsolationConfig:
    """隔离配置"""
    enable_group_memory_isolation: bool = False
    enable_group_isolation: bool = False
    enable_persona_isolation: bool = False


@dataclass
class ScheduledTasksConfig:
    """定时任务配置"""
    provider: str = ""
    enable_forgetting: bool = True
    enable_merging: bool = True


@dataclass
class HiddenConfig:
    """隐藏配置(内部参数)
    
    这些配置项不会在 WebUI 中展示，用于控制内部行为。
    支持运行时热修改，并自动持久化到 data/iris_memory/hidden_config.json
    """
    # Token 预算控制
    token_budget_max_tokens: int = 2000
    
    # 遗忘权重算法参数
    forgetting_lambda: float = 0.1          # 近因性衰减系数
    forgetting_threshold: float = 0.3       # 遗忘阈值
    
    # 调试配置
    debug_mode: bool = False                # 启用调试模式
    verbose_logging: bool = False           # 详细日志输出
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    # 性能调优
    chromadb_batch_size: int = 100          # ChromaDB 批量写入大小
    kuzu_query_timeout_ms: int = 5000       # KuzuDB 查询超时
    
    # L3 知识图谱参数
    entity_extraction_temperature: float = 0.3     # 实体提取温度
    type_merge_threshold: float = 0.8              # 类型合并相似度阈值
    node_confidence_threshold: float = 0.3         # 节点最低置信度
    edge_weight_decay_rate: float = 0.01           # 边权重衰减率
    forgetting_lambda_kg: float = 0.01             # 知识图谱遗忘系数
    forgetting_threshold_kg: float = 0.2           # 知识图谱遗忘阈值
    kg_retention_days: int = 30                    # 知识图谱保留天数


@dataclass
class Defaults:
    """所有默认配置的统一入口
    
    提供扁平化键名访问方法，支持 "l1_buffer.enable" 格式的键名。
    """
    l1_buffer: L1BufferConfig = field(default_factory=L1BufferConfig)
    l2_memory: L2MemoryConfig = field(default_factory=L2MemoryConfig)
    l3_kg: L3KGConfig = field(default_factory=L3KGConfig)
    image_parsing: ImageParsingConfig = field(default_factory=ImageParsingConfig)
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    enhancement: EnhancementConfig = field(default_factory=EnhancementConfig)
    isolation_config: IsolationConfig = field(default_factory=IsolationConfig)
    scheduled_tasks: ScheduledTasksConfig = field(default_factory=ScheduledTasksConfig)
    hidden: HiddenConfig = field(default_factory=HiddenConfig)
    
    def get_by_flat_key(self, flat_key: str) -> Optional[object]:
        """通过扁平化键名获取默认值
        
        Args:
            flat_key: 扁平化键名，支持两种格式：
                - "l1_buffer.enable" (用户配置)
                - "debug_mode" (隐藏配置)
        
        Returns:
            默认值，找不到返回 None
        
        Examples:
            >>> defaults = Defaults()
            >>> defaults.get_by_flat_key("l1_buffer.enable")
            True
            >>> defaults.get_by_flat_key("debug_mode")
            False
        """
        parts = flat_key.split(".")
        
        if len(parts) == 1:
            # 隐藏配置项(单层键名)
            return getattr(self.hidden, parts[0], None)
        elif len(parts) == 2:
            # 用户配置项(双层键名：section.key)
            section, key = parts
            section_config = getattr(self, section, None)
            if section_config is not None:
                return getattr(section_config, key, None)
        
        return None
    
    def get_section_defaults(self, section: str) -> Dict[str, object]:
        """获取指定配置分组的所有默认值
        
        Args:
            section: 配置分组名，如 "l1_buffer"
        
        Returns:
            配置字典
        
        Examples:
            >>> defaults = Defaults()
            >>> l1_defaults = defaults.get_section_defaults("l1_buffer")
            >>> print(l1_defaults["enable"])
            True
        """
        section_config = getattr(self, section, None)
        if section_config is None:
            return {}
        return asdict(section_config)
