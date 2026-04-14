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
    inject_queue_length: int = 30
    retain_message_count: int = 10
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
    max_parse_per_request: int = 5
    max_concurrent_parse: int = 3
    cache_retention_days: int = 7


@dataclass
class ProfileConfig:
    """画像系统配置"""
    enable: bool = True
    analysis_provider: str = ""
    analysis_mode: Literal["all", "related"] = "all"
    enable_auto_injection: bool = True


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
    enable_forgetting: bool = True       # 启用定时遗忘清洗任务
    enable_merging: bool = True


@dataclass
class WebConfig:
    """Web 服务器配置"""
    enable: bool = True
    host: str = "0.0.0.0"
    port: int = 9967
    access_key: str = ""


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
    enable_context_logging: bool = False    # 启用 LLM 上下文日志输出
    
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
    
    # LLM 调用管理参数
    call_log_max_entries: int = 100         # 调用日志最大保留条数
    
    # 定时任务参数
    forgetting_task_interval_hours: int = 6     # 遗忘清洗任务间隔（小时）
    merge_task_interval_hours: int = 24         # 合并任务间隔（小时）
    merge_similarity_threshold: float = 0.85    # 合并相似度阈值
    merge_batch_size: int = 10                  # 合并批处理大小
    eviction_batch_size: int = 100              # 淘汰批处理大小
    image_cache_cleanup_interval_hours: int = 24  # 图片缓存清理任务间隔（小时）
    
    # L3 知识图谱提取任务参数
    kg_extraction_interval_minutes: int = 30        # 提取任务检测间隔（分钟）
    kg_extraction_min_unprocessed: int = 10         # 最小未处理记忆数量阈值
    kg_extraction_batch_size: int = 20              # 每批处理记忆数
    kg_extraction_max_related: int = 5              # 每条记忆最多关联的相关记忆数
    kg_extraction_semantic_weight: float = 0.5      # 语义相似记忆权重
    kg_extraction_same_group_weight: float = 0.3    # 同群聊记忆权重
    kg_extraction_same_user_weight: float = 0.2     # 同用户记忆权重
    
    # Tool 配置参数
    tool_memory_max_content_length: int = 500          # 记忆内容最大长度
    tool_correction_require_confirmation: bool = False  # 修正需确认
    tool_timeout_ms: int = 2000                        # Tool调用超时
    tool_read_max_results: int = 10                    # 读取记忆最大返回数
    
    # Web 安全增强配置（可选）
    web_ssl_cert: str = ""                 # SSL 证书路径（启用 HTTPS）
    web_ssl_key: str = ""                  # SSL 私钥路径
    web_cors_origins: str = "*"            # CORS 允许的源（逗号分隔）
    web_enable_csrf_protection: bool = True  # 是否启用 CSRF 保护
    web_rate_limit_max_requests: int = 100  # 速率限制：每分钟最大请求数
    web_rate_limit_window_seconds: int = 60  # 速率限制：时间窗口（秒）
    
    
    # 画像系统参数
    profile_analysis_interval_hours: int = 24          # 分析任务间隔（小时）
    profile_max_messages_for_analysis: int = 50        # 分析时最大消息数
    profile_enable_version_control: bool = True        # 启用版本控制
    profile_mid_update_interval_summaries: int = 5     # 中期更新：每隔N次总结触发
    profile_mid_update_interval_hours: float = 24.0    # 中期更新：最短间隔（小时）
    profile_long_update_interval_hours: float = 168.0  # 长期更新：最短间隔（小时，默认7天）
    
    # 图片解析参数
    image_parsing_timeout_ms: int = 30000              # 图片解析超时（毫秒）
    image_parsing_max_size_kb: int = 4096              # 最大图片大小（KB）
    image_parsing_supported_formats: str = "jpg,jpeg,png,gif,webp"  # 支持的图片格式
    image_parsing_fallback_on_error: bool = True       # 解析失败时是否入队原始消息
    image_phash_enable: bool = True                    # 启用 pHash 感知哈希去重
    image_phash_threshold: int = 10                    # pHash 汉明距离阈值（越小越严格）
    image_filter_enable: bool = True                   # 启用无效图过滤（纯色/过小）
    image_filter_min_size: int = 16                    # 最小图片尺寸（像素）
    image_filter_std_threshold: float = 5.0            # 纯色检测标准差阈值
    
    # 输入清理参数
    input_sanitizer_enable: bool = True                # 启用 Prompt 注入过滤
    input_sanitizer_max_length: int = 10000            # 输入最大长度
    
    # 遗忘确认参数
    forgetting_llm_confirm_enable: bool = False        # 启用 LLM 最终兜底确认遗忘
    forgetting_llm_confirm_provider: str = ""          # 确认使用的 Provider（空则使用默认）
    forgetting_llm_confirm_threshold: float = 0.15     # 评分低于此值才触发 LLM 确认


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
    web: WebConfig = field(default_factory=WebConfig)
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
