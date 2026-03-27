# 实现计划

## 概览

### 阶段总览表

| 阶段 | 名称 | 核心产物 | 是否可跳过 |
|------|------|----------|------------|
| 1 | 基础设施搭建 | 配置系统、平台接口、日志框架、组件初始化 | 否 |
| 2 | L1 消息上下文缓冲 | 消息队列管理、自动总结 | 否 |
| 3 | L2 记忆库 | ChromaDB 集成、记忆存储与检索 | 否 |
| 4 | L3 知识图谱 | KuzuDB 集成、图谱存储与检索 | 否 |
| 5 | LLM 调用统一管理 | LLM 调用封装、Token 统计 | 否 |
| 6 | 定时任务系统 | 遗忘/合并/权重更新任务 | 否 |
| 7 | TOOL 钩子 | 记忆读写、画像获取、修正功能 | 否 |
| 8 | 记忆增强 | 图增强检索、重排序、Token 预算控制 | 是 |
| 9 | 画像系统 | 群聊画像、用户画像 | 是 |
| 10 | 图片解析 | 图片解析入上下文 | 是 |
| 11 | Web 模块展示 | 记忆可视化、画像编辑、统计图表 | 是 |

### 依赖拓扑简述

```
阶段1 → 阶段2 → 阶段3 → 阶段4 → 阶段5 → 阶段6 → 阶段7 → 阶段8
                                                    ↓
                                              阶段9/10/11（可并行）
```

- **串行依赖**：阶段 1-7 必须顺序执行，后续阶段依赖前阶段产物
- **可并行**：阶段 8、9、10、11 为附加功能，可在阶段 7 完成后并行开发

---

## 阶段 1：基础设施搭建

**目标**：插件可独立启动并加载，配置系统可通过 WebUI 修改，日志输出带模块标识，各组件初始化框架就绪。

**涉及模块**：
- config 统一管理
- 平台接口统一管理
- 日志管理
- 组件初始化框架

**实现步骤**：

1. **创建插件骨架与元数据**
   - 创建 `metadata.yaml`，声明插件名称、版本、兼容 AstrBot 版本（`>=4.16,<5`）
   - 创建 `_conf_schema.json`，定义用户可见配置项：
     - **L1 Buffer**: enable、summary_provider、inject_queue_length、max_queue_tokens、max_single_message_tokens
     - **L2 Memory**: enable、summary_provider、top_k、max_entries、timeout_ms、enable_graph_enhancement
     - **L3 KG**: enable、max_nodes、max_edges、timeout_ms
     - **图片解析**: enable、provider、parsing_mode(all/related)、daily_quota
     - **画像系统**: enable、analysis_mode(all/related)
     - **记忆增强**: enable_rerank、rerank_provider
     - **隔离配置**: enable_group_memory_isolation、enable_group_isolation、enable_persona_isolation
     - **定时任务**: provider、enable_forgetting、enable_merging
   - 创建 `requirements.txt`，声明依赖：`chromadb`、`kuzu`
   - 为什么：AstrBot 通过 `metadata.yaml` 识别插件，`_conf_schema.json` 生成 WebUI 配置表单

2. **实现 config 统一管理模块** (`iris_memory/config/`)
   - 使用 dataclasses 定义配置结构，支持扁平化键名访问和配置项分类管理
   - 提供线程安全的配置管理和观察者模式
   - 已完成实现，详见【注意事项】中的使用说明
   - 为什么：配置系统是所有模块的基础，需先就绪

3. **实现平台接口统一管理模块** (`iris_memory/platform/`) ✅ **已完成**
   - 定义 `PlatformAdapter` 抽象类，声明获取用户 ID、用户名、群 ID、群名称等接口
   - 实现 `OneBot11Adapter`（QQ 平台），从 `AstrMessageEvent` 提取平台原始 ID
   - 实现适配器工厂方法，根据 `event.platform_adapter_type` 返回对应适配器
   - 额外实现：用户昵称、角色识别、群聊判断、原始消息访问、扩展接口
   - 为什么：平台差异需在上层屏蔽，后续模块统一调用

4. **集成 AstrBot 日志系统** (`iris_memory/core/logger.py`) ✅ **已完成**
   - 使用 `logging.getLogger("astrbot")` 获取 AstrBot 日志器
   - 封装 `get_logger(submodule: str)` 函数，返回带 `[iris-memory:{submodule}]` 前缀的日志器
   - 为什么：AstrBot 统一管理日志，但需区分模块来源

5. **实现组件初始化框架** (`iris_memory/core/components.py`)
   - 定义 `Component` 抽象基类，声明 `initialize()` 和 `shutdown()` 方法
   - 实现 `ComponentManager` 类，管理组件生命周期
   - 各组件初始化失败时记录日志但不阻塞其他组件启动
   - 为什么：后续 ChromaDB、KuzuDB、定时任务等需统一初始化入口

**完成标志**：
- 插件可被 AstrBot 加载，在 WebUI 插件列表显示
- 修改配置后点击"重载插件"，配置值更新生效
- 日志输出带 `[iris-memory:xxx]` 前缀

**阶段产物**：
- `metadata.yaml`
- `_conf_schema.json`
- `requirements.txt`
- `iris_memory/config/`
- `iris_memory/platform/`
- `iris_memory/core/logger.py`
- `iris_memory/core/components.py`
- `main.py`（插件入口，继承 `Star`）

---

## 阶段 2：L1 消息上下文缓冲

**目标**：消息可按群聊入队，队列满时触发自动总结，总结结果可写入 L2 记忆库（若已初始化）。

**涉及模块**：
- L1 普通消息上下文缓冲
- L1 补充层 LLM 消息上下文管理接口

**实现步骤**：

1. **定义消息数据结构** (`iris_memory/models/message.py`)
   - 定义 `ContextMessage` 数据类：`role`、`content`、`timestamp`、`token_count`、`source`
   - 定义 `MessageQueue` 数据类：`group_id`、`messages`（`collections.deque`）、`max_length`、`max_tokens`
   - 为什么：统一消息格式是后续处理的基础

2. **实现消息队列管理器** (`iris_memory/context_buffer.py`)
   - 定义 `ContextBufferManager` 类，管理多个群聊的消息队列（`dict[group_id, MessageQueue]`）
   - 实现 `add_message(group_id, message)` 方法：
     - 单条消息超过 token 上限时直接舍弃，不入队
     - 入队后检查队列长度与总 token，满足条件时触发总结
   - 实现 `get_context(group_id)` 方法，返回当前队列消息列表
   - 实现 `clear_context(group_id)` 方法，清空指定群聊队列
   - 为什么：队列是 L1 层核心数据结构

3. **实现 Token 计数工具** (`iris_memory/utils/token_counter.py`)
   - 使用 `tiktoken` 库实现 Token 计数（默认 `cl100k_base` 编码）
   - 封装 `count_tokens(text: str) -> int` 函数
   - 为什么：队列管理依赖 Token 计数做容量控制

4. **实现自动总结触发逻辑** (`iris_memory/summarizer.py`)
   - 定义 `Summarizer` 类，依赖 LLM 调用接口（阶段 5 提供，此处先定义接口）
   - 实现 `should_summarize(queue: MessageQueue) -> bool`：
     - 队列长度 > 配置的 `inject_queue_length`
     - 总 token > 配置的 `max_queue_tokens`（与注入上下文数量无关）
   - 实现 `summarize(messages: List[ContextMessage]) -> str`，调用 LLM 总结
     - 使用配置的 `summary_provider`，若为空则使用默认 Provider
   - 总结完成后自动触发权重更新（图谱节点访问频率、边权重）
   - 为什么：总结是压缩上下文的核心机制

5. **集成 AstrBot 消息钩子** (`main.py`)
   - 使用 `@filter.on_llm_request()` 钩子，在 LLM 调用前将队列消息加入 `contexts`
   - 使用 `@filter.on_llm_response()` 钩子，在 LLM 响应后更新队列（若 LLM 消息上下文控制开启）
   - 为什么：通过钩子将 L1 缓冲与 AstrBot 主流程对接

**完成标志**：
- 发送多条消息后，通过日志可见消息入队
- 队列满时触发自动总结，日志显示总结结果
- 触发 LLM 时，上下文包含队列消息

**阶段产物**：
- `iris_memory/models/message.py`
- `iris_memory/context_buffer.py`
- `iris_memory/utils/token_counter.py`
- `iris_memory/summarizer.py`
- `main.py`（新增钩子处理）

---

## 阶段 3：L2 记忆库

**目标**：可存储记忆向量，支持群聊隔离检索，ChromaDB 不可用时自动降级。

**涉及模块**：
- ChromaDB 集成
- 群聊 ID 隔离
- 去重逻辑
- 独立降级
- 冷启动兜底
- 响应延迟保护

**实现步骤**：

1. **定义记忆数据结构** (`iris_memory/models/memory.py`)
   - 定义 `MemoryEntry` 数据类：`id`、`content`、`metadata`（含 `group_id`、`timestamp`、`confidence`、`access_count`、`last_access_time`）
   - 定义 `MemorySearchResult` 数据类：`entry`、`score`
   - 为什么：统一记忆格式，便于序列化与检索

2. **实现 ChromaDB 适配器** (`iris_memory/storage/chroma_adapter.py`)
   - 定义 `ChromaAdapter` 类，实现 `Component` 接口
   - 实现 `initialize()`：连接 ChromaDB，创建 `default` collection，检查人格隔离配置创建对应 collection
   - 实现 `add_memory(entry: MemoryEntry)`：写入记忆，带去重检查（基于 `content` 哈希）
   - 实现 `search(query: str, group_id: str, top_k: int, timeout_ms: int) -> List[MemorySearchResult]`：
     - 设置超时保护（使用 `asyncio.wait_for`）
     - 超时后返回空列表
   - 实现 `update_memory(id: str, updates: dict)`：更新记忆元数据
   - 实现 `delete_memory(id: str)`：删除记忆
   - 为什么：ChromaDB 是 L2 层核心存储

3. **实现记忆检索器** (`iris_memory/retrievers/memory_retriever.py`)
   - 定义 `MemoryRetriever` 类，依赖 `ChromaAdapter`
   - 实现 `retrieve(query: str, group_id: str, top_k: int) -> List[MemorySearchResult]`
   - 实现 `add_from_summary(summary: str, group_id: str)`：从总结文本写入记忆
     - 使用配置的 `summary_provider` 调用 LLM 提取记忆要点
     - 若 `summary_provider` 为空则使用默认 Provider
   - 总结完成后自动触发权重更新（记忆访问频率更新）
   - **图增强检索**（用户可见配置）：
     - 配置项：`enable_graph_enhancement`
     - 触发时机：L2 记忆检索完成后
     - 执行逻辑：
       1. 从 L2 检索结果中提取实体 ID
       2. 调用 `GraphRetriever.expand_from_memory()` 在 L3 图谱中查找关联关系
       3. 将图谱关系合并到检索结果中
     - 目的：发现 L2 记忆未直接返回但相关的图谱关系
   - 为什么：封装检索逻辑，供上层统一调用

4. **实现降级与兜底逻辑** (`iris_memory/storage/fallback.py`)
   - 在 `ChromaAdapter` 初始化失败时，设置 `is_available = False`
   - 检索时检查 `is_available`，为 `False` 时返回空列表
   - 新用户/新群聊首次检索时，直接返回空列表
   - 为什么：保证 L2 失效不影响 L1 和主流程

5. **集成到消息钩子** (`main.py`)
   - 在 `@filter.on_llm_request()` 中调用 `MemoryRetriever.retrieve()`，将检索结果加入上下文
   - 在总结完成后调用 `MemoryRetriever.add_from_summary()` 写入记忆
   - 为什么：将 L2 检索与 L1 缓冲联动

**完成标志**：
- 总结后可在 ChromaDB 中查到记忆
- 发送相似问题时，检索结果出现在上下文中
- ChromaDB 连接断开后，主流程不报错，日志显示降级

**阶段产物**：
- `iris_memory/models/memory.py`
- `iris_memory/storage/chroma_adapter.py`
- `iris_memory/retrievers/memory_retriever.py`
- `iris_memory/storage/fallback.py`
- `data/chromadb/`（持久化目录）

---

## 阶段 4：L3 知识图谱

**目标**：可存储知识节点与关系边，支持人格隔离，KuzuDB 不可用时自动降级。

**涉及模块**：
- KuzuDB 集成
- 人格隔离
- 独立降级
- 冷启动兜底
- 响应延迟保护
- 容量上限与淘汰策略
- 遗忘权重算法

**实现步骤**：

1. **定义图谱数据结构** (`iris_memory/models/graph.py`)
   - 定义 `GraphNode` 数据类：`id`、`type`、`properties`、`confidence`、`access_count`、`last_access_time`
   - 定义 `GraphEdge` 数据类：`source_id`、`target_id`、`type`、`properties`、`weight`
   - 为什么：统一图谱数据格式

2. **实现 KuzuDB 适配器** (`iris_memory/storage/kuzu_adapter.py`)
   - 定义 `KuzuAdapter` 类，实现 `Component` 接口
   - 实现 `initialize()`：
     - 创建数据库文件（存放于 `data/kuzu/`）
     - 创建节点/边 schema：`Node(id, type, confidence, access_count, last_access_time, isolation_degree)`
     - 创建 default 图及人格隔离图
   - 实现 `add_node(node: GraphNode)`、`add_edge(edge: GraphEdge)`
   - 实现 `query(cypher: str, timeout_ms: int) -> List[dict]`：
     - 设置超时保护
     - 超时后返回空列表
   - 实现 `update_node(id: str, updates: dict)`
   - 实现 `delete_node(id: str)`：同时删除关联边
   - 为什么：KuzuDB 是 L3 层核心存储

3. **实现遗忘权重算法** (`iris_memory/utils/forgetting.py`)
   - 实现 `calculate_forgetting_score(entry, now: datetime) -> float`：
     - R（近因性）：`exp(-λ * Δt)`，λ 从 config 读取
     - F（频率性）：归一化访问次数
     - C（置信度）：从 metadata 读取
     - D（孤立度）：仅图谱节点，计算孤立边比例
     - 加权求和
   - 实现 `should_evict(score: float, last_access_time: datetime, config: Config) -> bool`
   - 为什么：统一 L2 和 L3 的淘汰逻辑

4. **实现图谱检索器** (`iris_memory/retrievers/graph_retriever.py`)
   - 定义 `GraphRetriever` 类，依赖 `KuzuAdapter`
   - 实现 `retrieve(node_ids: List[str]) -> List[GraphEdge]`：根据节点 ID 查关联边
   - 实现 `expand_from_memory(memories: List[MemorySearchResult]) -> List[GraphEdge]`：
     - 从 L2 记忆中提取实体
     - 在图谱中查找关联关系
   - **L3 检索 vs 图增强检索的区别**：
     - **L3 检索（图谱检索）**：
       - 独立的检索层，直接从 KuzuDB 检索节点和边
       - 作为 L2 记忆检索的补充检索层
       - 返回图谱中的实体关系数据
       - 触发条件：每次 LLM 请求时，L2 检索后触发 L3 检索
     - **图增强检索**：
       - 记忆增强模块的功能，不是独立检索层
       - 基于 L2 检索结果进行扩展
       - 从 L2 记忆中提取实体 ID，在图谱中查找关联关系
       - 目的：发现 L2 记忆未直接返回但相关的图谱关系
       - 触发条件：仅在启用记忆增强时，对 L2+L3 合并结果进行扩展
   - 为什么：支持图增强检索

5. **实现容量上限与淘汰** (`iris_memory/storage/eviction.py`)
   - 定义 `EvictionManager` 类
   - 实现 `check_and_evict()`：
     - 检查 L2 条目数、L3 节点数是否超限
     - 计算遗忘权重评分
     - 批量淘汰评分最低的条目
   - 为什么：控制存储容量，防止无限增长

**完成标志**：
- 总结后可在 KuzuDB 中查到节点和边
- 发送相关问题时，图谱关系被检索
- KuzuDB 不可用时，日志显示降级，主流程正常

**阶段产物**：
- `iris_memory/models/graph.py`
- `iris_memory/storage/kuzu_adapter.py`
- `iris_memory/utils/forgetting.py`
- `iris_memory/retrievers/graph_retriever.py`
- `iris_memory/storage/eviction.py`
- `data/kuzu/`（持久化目录）

---

## 阶段 5：LLM 调用统一管理

**目标**：提供统一的 LLM 调用入口，支持 Token 统计与调用模块追踪。

**涉及模块**：
- LLM 调用封装
- Token 统计
- 调用模块追踪

**实现步骤**：

1. **实现 LLM 调用管理器** (`iris_memory/llm/manager.py`)
   - 定义 `LLMManager` 类
   - 实现 `generate(prompt: str, module: str, **kwargs) -> LLMResponse`：
     - 调用 `self.context.llm_generate()`
     - 记录 Token 使用量、调用模块
   - 实现 `generate_with_tools(prompt: str, tools: List, module: str, **kwargs) -> LLMResponse`：
     - 调用 `self.context.tool_loop_agent()`
     - 记录统计信息
   - 为什么：统一入口便于管理与统计

2. **实现 Token 统计模块** (`iris_memory/llm/token_stats.py`)
   - 定义 `TokenStats` 数据类：`total_input_tokens`、`total_output_tokens`、`by_module: Dict[str, TokenUsage]`
   - 定义 `TokenStatsManager` 类：
     - 实现 `record(module: str, input_tokens: int, output_tokens: int)`
     - 实现 `get_stats() -> TokenStats`
     - 实现 `reset()`：重置统计（每日 UTC 00:00）
   - 为什么：统计 Token 消耗，供 WebUI 展示

3. **实现调用记录存储** (`iris_memory/llm/call_log.py`)
   - 定义 `CallLog` 数据类：`timestamp`、`module`、`input_tokens`、`output_tokens`、`duration_ms`
   - 使用 `deque` 存储最近 N 条调用记录（可配置）
   - 为什么：供调试与分析

4. **集成到总结与检索** (`iris_memory/summarizer.py`, `iris_memory/retrievers/`)
   - 替换直接调用 `self.context.llm_generate()` 为 `LLMManager.generate()`
   - 为什么：统一调用路径

**完成标志**：
- 总结与检索时，日志显示 Token 使用量
- 调用统计可通过接口查询

**阶段产物**：
- `iris_memory/llm/manager.py`
- `iris_memory/llm/token_stats.py`
- `iris_memory/llm/call_log.py`

---

## 阶段 6：定时任务系统

**目标**：定时任务可按配置执行，不阻塞主流程，写竞争保护生效。

**涉及模块**：
- 清理与整理专项任务
- 写竞争保护

**实现步骤**：

1. **实现任务调度器** (`iris_memory/tasks/scheduler.py`)
   - 定义 `TaskScheduler` 类，实现 `Component` 接口
   - 使用 `asyncio` 实现定时任务调度
   - 实现任务队列串行调度，同一时刻只有一项任务持有写锁
   - 为什么：统一管理定时任务

2. **实现遗忘清洗任务** (`iris_memory/tasks/forgetting_task.py`)
   - 定义 `ForgettingTask` 类
   - 实现 `run()`：
     - 计算 L2 和 L3 遗忘评分
     - 批量淘汰评分低于阈值且超过保留期的条目
     - 标记低置信度记忆待复核
     - 使用配置的 `provider` 调用 LLM 确认删除（可选）
   - 为什么：定期清理过期记忆，保证数据质量

3. **实现合并任务** (`iris_memory/tasks/merge_task.py`)
   - 定义 `MergeTask` 类
   - 实现 `run()`：
     - 检索相似记忆
     - 使用配置的 `provider` 调用 LLM 合并为长文本
     - 更新存储
   - 为什么：减少记忆碎片

**完成标志**：
- 定时任务按配置时间执行
- 日志显示任务执行结果
- 多任务并行时不发生写冲突

**阶段产物**：
- `iris_memory/tasks/scheduler.py`
- `iris_memory/tasks/forgetting_task.py`
- `iris_memory/tasks/merge_task.py`

---

## 阶段 7：TOOL 钩子

**目标**：LLM 可通过 Tool 调用保存/读取记忆、获取画像、修正错误。

**涉及模块**：
- 保存记忆
- 读取记忆
- 获取群聊画像
- 获取用户画像
- 修正功能

**实现步骤**：

1. **实现保存记忆 Tool** (`iris_memory/tools/save_memory.py`)
   - 使用 `@filter.llm_tool(name="save_memory")` 装饰器
   - 实现 `save_memory(content: str, confidence: str)`：
     - 写入 ChromaDB 和 KuzuDB
     - 返回操作结果
   - 为什么：让 LLM 主动保存重要信息

2. **实现读取记忆 Tool** (`iris_memory/tools/read_memory.py`)
   - 使用 `@filter.llm_tool(name="read_memory")` 装饰器
   - 实现 `read_memory(query: str, top_k: int)`：
     - 调用 `MemoryRetriever.retrieve()`
     - 返回记忆列表
   - 为什么：让 LLM 主动检索记忆

3. **实现获取群聊画像 Tool** (`iris_memory/tools/get_group_profile.py`)
   - 使用 `@filter.llm_tool(name="get_group_profile")` 装饰器
   - 实现 `get_group_profile(group_id: str)`：
     - 若画像模块未实现，返回提示信息
     - 否则返回画像数据
   - 为什么：让 LLM 了解群聊特征

4. **实现获取用户画像 Tool** (`iris_memory/tools/get_user_profile.py`)
   - 使用 `@filter.llm_tool(name="get_user_profile")` 装饰器
   - 实现 `get_user_profile(user_id: str, group_id: str)`：
     - 若画像模块未实现，返回提示信息
     - 否则返回画像数据（考虑群聊隔离）
   - 为什么：让 LLM 了解用户特征

5. **实现修正 Tool** (`iris_memory/tools/correct_memory.py`)
   - 使用 `@filter.llm_tool(name="correct_memory")` 装饰器
   - 实现 `correct_memory(memory_id: str, correction: str)`：
     - 更新 ChromaDB 条目
     - 标记 KuzuDB 关联节点为"待复核"
   - 为什么：支持用户纠正幻觉

**完成标志**：
- LLM 可通过 Tool 调用保存/读取记忆
- 修正操作后，存储数据更新

**阶段产物**：
- `iris_memory/tools/save_memory.py`
- `iris_memory/tools/read_memory.py`
- `iris_memory/tools/get_group_profile.py`
- `iris_memory/tools/get_user_profile.py`
- `iris_memory/tools/correct_memory.py`

---

## 阶段 8：记忆增强（附加功能）

**目标**：记忆检索质量提升，支持重排序（用户配置）、图增强检索（用户配置）和 Token 预算控制（隐藏配置）。

**涉及模块**：
- 重排序增强（用户配置，由 AstrBot 管理）
- 图增强检索（用户配置，由 AstrBot 管理）
- Token 预算控制（隐藏配置，通过自定义 Web 路由管理，阶段11实现）

**实现步骤**：

1. **实现重排序** (`iris_memory/enhancement/reranker.py`)
   - 定义 `Reranker` 类
   - 实现 `rerank(query: str, results: List[MemorySearchResult], top_k: int) -> List[MemorySearchResult]`：
     - 使用配置的 `rerank_provider` 调用轻量模型重排序
     - 若 `rerank_provider` 为空则使用默认 Provider
     - 返回 Top-K 结果
   - 为什么：提高检索精度（用户可选择启用）

2. **实现图增强检索集成** (`iris_memory/enhancement/graph_enhancement.py`)
   - 定义 `GraphEnhancer` 类
   - 实现 `enhance(memories: List[MemorySearchResult]) -> List[MemorySearchResult]`：
     - 调用 `GraphRetriever.expand_from_memory()`
     - 合并图谱关系结果
   - **说明**：图增强检索功能在 L2 记忆层配置（`enable_graph_enhancement`），此处仅实现集成逻辑
   - **完整检索流程**：
     ```
     用户提问
       ↓
     L1 缓冲注入上下文
       ↓
     L2 记忆检索（ChromaDB）→ 返回相关记忆向量
       ↓
     [图增强检索]（可选，L2配置）
       └─ 从 L2 结果提取实体，查找关联图谱关系
       ↓
     L3 图谱检索（KuzuDB）→ 返回图谱节点和边
       ↓
     [记忆增强模块]（可选）
       ├─ 重排序：对 L2+L3 结果进行重排序
       └─ Token 预算控制：截断结果以控制注入量
       ↓
     最终结果注入 LLM 上下文
     ```
   - **关键区别总结**：
     - **L2 检索**：向量相似度检索，返回语义相关的记忆文本
     - **L3 检索**：图谱结构检索，返回实体关系网络
     - **图增强检索**：利用 L3 图谱扩展 L2 结果，发现更多关联信息（L2 层配置）
   - 为什么：利用图谱关系扩展检索结果

3. **实现 Token 预算控制** (`iris_memory/enhancement/token_budget.py`)
   - 定义 `TokenBudgetController` 类
   - 实现 `truncate_to_budget(results: List[MemorySearchResult], budget: int) -> List[MemorySearchResult]`：
     - 计算 Token 数
     - 按重要性截断
   - 为什么：防止记忆注入溢出上下文（隐藏配置控制）

**完成标志**：
- 重排序后 Top-K 结果相关性更高
- 图增强检索可扩展相关记忆
- 注入记忆不超过 Token 预算

**阶段产物**：
- `iris_memory/enhancement/reranker.py`
- `iris_memory/enhancement/graph_enhancement.py`
- `iris_memory/enhancement/token_budget.py`

---

## 阶段 9：画像系统（附加功能）

**目标**：群聊画像与用户画像可存储、更新、检索。

**涉及模块**：
- 群聊画像
- 用户画像
- 分析模式
- 版本控制

**实现步骤**：

1. **定义画像数据结构** (`iris_memory/models/profile.py`)
   - 定义 `GroupProfile` 数据类
   - 定义 `UserProfile` 数据类
   - 为什么：统一画像格式

2. **实现画像存储** (`iris_memory/storage/profile_storage.py`)
   - 定义 `ProfileStorage` 类
   - 使用 JSON 文件存储（`data/profiles/`）
   - 实现读写方法，带版本号控制
   - 为什么：画像需持久化

3. **实现画像管理器** (`iris_memory/profiles/profile_manager.py`)
   - 定义 `ProfileManager` 类
   - 实现 `get_group_profile(group_id: str) -> GroupProfile`
   - 实现 `get_user_profile(user_id: str, group_id: str) -> UserProfile`
   - 实现 `update_group_profile(group_id: str, updates: dict)`
   - 实现 `update_user_profile(user_id: str, group_id: str, updates: dict)`
   - 为什么：封装画像操作

4. **实现画像分析器** (`iris_memory/profiles/profile_analyzer.py`)
   - 定义 `ProfileAnalyzer` 类
   - 实现 `analyze_group(messages: List[ContextMessage]) -> dict`：
     - 根据 `analysis_mode` 配置决定分析消息范围：
       - `all`: 分析所有消息
       - `related`: 仅分析对话相关的消息
     - 调用 LLM 分析群聊特征
   - 实现 `analyze_user(messages: List[ContextMessage]) -> dict`：
     - 根据 `isolation_config.enable_group_isolation` 决定画像索引：
       - 开启: 使用群号作为画像索引
       - 关闭: 使用 `"default"` 作为画像索引
     - 调用 LLM 分析用户特征
   - 为什么：自动化画像更新

**完成标志**：
- 总结后画像自动更新
- Tool 可获取画像数据

**阶段产物**：
- `iris_memory/models/profile.py`
- `iris_memory/storage/profile_storage.py`
- `iris_memory/profiles/profile_manager.py`
- `iris_memory/profiles/profile_analyzer.py`
- `data/profiles/`

---

## 阶段 10：图片解析（附加功能）

**目标**：图片可按模式解析入上下文，支持每日限额。

**涉及模块**：
- 图片解析模式
- 每日解析限额
- 图片去重与过滤

**实现步骤**：

1. **实现图片处理器** (`iris_memory/image/processor.py`)
   - 定义 `ImageProcessor` 类
   - 实现 `process(image_path: str) -> str`：
     - pHash 去重
     - 纯色/过小图过滤
     - 使用配置的 `provider` 调用 LLM Vision 解析
     - 若 `provider` 为空则使用默认 Provider
   - 为什么：图片处理核心逻辑

2. **实现每日限额管理** (`iris_memory/image/quota.py`)
   - 定义 `ImageQuotaManager` 类
   - 使用 JSON 文件存储计数器（`data/image_quota.json`）
   - 实现 `check_and_consume() -> bool`：检查并消耗额度
   - 实现 `reset()`：每日 UTC 00:00 重置
   - 为什么：控制图片解析成本

3. **集成到消息钩子** (`main.py`)
   - 在 `@filter.on_llm_request()` 中检查图片消息
   - 根据 `parsing_mode` 配置决定是否处理：
     - `all`: 处理所有图片
     - `related`: 仅处理触发 LLM/被引用/OCR 命中的图片
   - 检查每日限额 `daily_quota`，超限则跳过
   - 解析结果加入上下文
   - 为什么：将图片解析接入主流程

**完成标志**：
- 发送图片后，上下文包含图片描述
- 超过每日限额后，图片被跳过

**阶段产物**：
- `iris_memory/image/processor.py`
- `iris_memory/image/quota.py`
- `data/image_quota.json`

---

## 阶段 11：Web 模块展示（附加功能）

**目标**：可通过 AstrBot WebUI 查看记忆、编辑画像、查看统计。

**涉及模块**：
- 记忆可视化
- 画像编辑
- Token 统计图表
- 数据删除

**实现步骤**：

1. **实现 Web 路由注册** (`iris_memory/web/routes.py`)
   - 使用 AstrBot Dashboard 鉴权体系
   - 注册 API 路由
   - 为什么：集成到 AstrBot WebUI

2. **实现记忆可视化 API** (`iris_memory/web/memory_api.py`)
   - 实现 `GET /api/memory/list`：列出记忆
   - 实现 `GET /api/memory/search`：搜索记忆
   - 实现 `DELETE /api/memory/{id}`：删除记忆
   - 为什么：提供记忆管理接口

3. **实现画像编辑 API** (`iris_memory/web/profile_api.py`)
   - 实现 `GET /api/profile/group/{id}`：获取群聊画像
   - 实现 `PUT /api/profile/group/{id}`：更新群聊画像
   - 实现 `GET /api/profile/user/{id}`：获取用户画像
   - 实现 `PUT /api/profile/user/{id}`：更新用户画像
   - 为什么：提供画像管理接口

4. **实现统计图表 API** (`iris_memory/web/stats_api.py`)
   - 实现 `GET /api/stats/tokens`：获取 Token 统计
   - 实现 `GET /api/stats/calls`：获取调用统计
   - 为什么：提供统计展示接口

**完成标志**：
- 通过 WebUI 可查看记忆列表
- 可编辑画像
- 可查看 Token 统计图表

**阶段产物**：
- `iris_memory/web/routes.py`
- `iris_memory/web/memory_api.py`
- `iris_memory/web/profile_api.py`
- `iris_memory/web/stats_api.py`

---

## 阶段依赖关系

```
阶段1（基础设施）
    ↓
阶段2（L1 缓冲）←→ 阶段5（LLM 管理）[双向依赖，阶段5先定义接口]
    ↓                   ↓
阶段3（L2 记忆库）←──────┘
    ↓
阶段4（L3 图谱）
    ↓
阶段6（定时任务）
    ↓
阶段7（TOOL 钩子）
    ↓
    ├── 阶段8（记忆增强）[可并行]
    ├── 阶段9（画像系统）[可并行]
    ├── 阶段10（图片解析）[可并行]
    └── 阶段11（Web 模块）[可并行]
```

**串行依赖说明**：
- 阶段 2 依赖阶段 1 的配置与日志系统
- 阶段 3 依赖阶段 2 的总结输出
- 阶段 4 依赖阶段 3 的记忆数据（图谱节点从记忆提取）
- 阶段 5 需在阶段 2 前定义接口，阶段 2 实现后再完善
- 阶段 6 依赖阶段 3、4 的存储组件
- 阶段 7 依赖阶段 3、4 的存储与阶段 5 的 LLM 调用

**可并行阶段说明**：
- 阶段 8-11 为附加功能，互不依赖，可在阶段 7 完成后并行开发

---

## 注意事项

### Config 模块使用方法

配置系统已实现完成，提供统一的配置管理接口。

**初始化（插件入口）**：
```python
# main.py
from pathlib import Path
from iris_memory.config import init_config

class IrisTierMemoryPlugin(Star):
    def __init__(self, context: StarContext, config: AstrBotConfig):
        super().__init__(context)
        data_dir = Path(context.get_data_dir())
        self.config = init_config(config, data_dir)
```

**其他模块使用**：
```python
# 方式1：全局函数（推荐）
from iris_memory.config import get_config

config = get_config()
enable_l1 = config.get("l1_buffer.enable")      # 用户配置
debug_mode = config.get("debug_mode")           # 隐藏配置

# 方式2：字典访问（不推荐）
enable_l1 = config["l1_buffer"]["enable"]

# 方式3：依赖注入（不推荐）
class MyComponent:
    def __init__(self, config: Config):
        self.max_tokens = config.get("l1_buffer.max_queue_tokens")
```

**热修改隐藏配置**：
```python
config = get_config()
config.set_hidden("debug_mode", True)
config.set_hidden("token_budget_max_tokens", 3000)
```

**注意**：
- 隐藏配置项不在 _conf_schema.json 中定义，不会与用户配置冲突
- 隐藏配置通过自定义 Web 路由管理（阶段11实现）
- 隐藏配置支持热修改，修改后立即生效并持久化到 `data/iris_memory/hidden_config.json`

**配置变更监听**：
```python
def on_config_change(key: str, old_value, new_value):
    if key == "debug_mode":
        logger.info(f"调试模式已切换：{old_value} → {new_value}")

config.on_config_change(on_config_change)
```

**配置优先级**：
- **用户配置项**（在 _conf_schema.json 中定义）：用户配置 > 默认值
- **隐藏配置项**（不在 _conf_schema.json 中定义）：隐藏配置 > 默认值
- **注意**：用户配置和隐藏配置不会冲突，因为它们的配置项完全不同

**文件位置**：
- `iris_memory/config/` - 配置模块目录
- Astrbot插件存储下`iris_memory/hidden_config.json` - 隐藏配置持久化文件

**配置项清单**：
- **用户配置**（由astrbot管理，_conf_schema.json 定义）：
  - L1 Buffer: `enable`, `summary_provider`, `inject_queue_length`, `max_queue_tokens`, `max_single_message_tokens`
  - L2 Memory: `enable`, `summary_provider`, `enable_graph_enhancement`, `top_k`, `max_entries`, `timeout_ms`
  - L3 KG: `enable`, `max_nodes`, `max_edges`, `timeout_ms`
  - 图片解析: `enable`, `provider`, `parsing_mode`, `daily_quota`
  - 画像系统: `enable`, `analysis_mode`
  - 记忆增强: `enable_rerank`, `rerank_provider`
  - 隔离配置: `enable_group_memory_isolation`, `enable_group_isolation`, `enable_persona_isolation`
  - 定时任务: `provider`, `enable_forgetting`, `enable_merging`
- **隐藏配置**（通过自定义 Web 路由管理，阶段11实现）：
  - `debug_mode`: 调试模式开关
  - `verbose_logging`: 详细日志开关
  - `token_budget_max_tokens`: Token 预算控制
  - `forgetting_lambda`: 遗忘权重算法参数
  - `forgetting_threshold`: 遗忘阈值
  - `chromadb_batch_size`: ChromaDB 批处理大小
  - `kuzu_query_timeout_ms`: KuzuDB 查询超时时间
  - 其他

---

### 方案标注注意点汇总

1. **隔离策略**
   - **人格隔离（第一层索引）**
     - 开启时：使用人格 ID 作为记忆存储和用户画像的第一层索引
     - 关闭时：使用 `"default"` 作为第一层索引
     - 影响范围：ChromaDB collection 命名、KuzuDB 图命名空间、用户画像存储路径
   - **群聊隔离（第二层索引）**
     - **记忆存储**：
       - 总是记录群聊 ID 到记忆元数据
       - 开启群聊记忆隔离时：群聊 ID 作为检索筛选条件
       - 关闭群聊记忆隔离时：不使用群聊 ID 筛选，全局共享记忆
     - **用户画像**：
       - 开启群聊用户画像隔离时：使用群号作为画像索引
       - 关闭群聊用户画像隔离时：使用 `"default"` 作为画像索引
   - 切换操作加互斥锁，防止读取混合命名空间数据
   - 切换群聊用户画像隔离会导致用户画像重建
   - 实现位置：`config.py`、`chroma_adapter.py`、`kuzu_adapter.py`、`profile_manager.py`

2. **记忆增强**
   - 提供开关控制（配置项）
   - **图增强检索**：用户配置（L2 记忆层），配置项 `enable_graph_enhancement`，由 AstrBot 管理
   - **重排序**：用户配置（记忆增强模块），可选择 `rerank_provider`，由 AstrBot 管理
   - **Token 预算控制**：隐藏配置，通过自定义 Web 路由管理（阶段11实现）
   - 实现位置：`enhancement/` 模块、`retrievers/memory_retriever.py`

3. **日志管理**
   - 使用 AstrBot 统一日志系统
   - 所有日志输出带 `[iris-memory:{submodule}]` 前缀
   - 调试级别日志可配置开关
   - 实现位置：`iris_memory/core/logger.py`

4. **组件初始化**
   - 各组件独立初始化，互不依赖
   - 某组件失败只影响对应层功能，其余继续运行
   - 全部组件失败时以仅 L1 模式运行
   - 实现位置：`components/__init__.py`

5. **热重启策略**
   - 重启时清空内存中的 L1 缓冲
   - 依靠 ChromaDB/KuzuDB 持久化存储恢复长期状态
   - 配置支持热修改（原子操作替换）
   - 实现位置：`config.py`、`main.py`

6. **写竞争保护**
   - 定时任务通过任务队列串行调度
   - ChromaDB 和 KuzuDB 分别加写锁，互不嵌套
   - 异步总结任务写入前检查 LLM 检索状态
   - 实现位置：`tasks/scheduler.py`、`tasks/summary_task.py`

7. **数据持久化目录**
   - 所有数据存放在 AstrBot 的 `data/` 目录下
   - 路径结构：`data/iris_memory/chromadb/`、`data/iris_memory/kuzu/`、`data/iris_memory/profiles/`
   - 实现位置：各存储适配器初始化时构建路径

8. **输入清洗**
   - 对所有外部输入执行 Prompt 注入过滤
   - 集中在输入网关层处理
   - 实现位置：`iris_memory/utils/input_sanitizer.py`（需新增）

9. **权重更新机制**
   - 权重更新不再作为独立定时任务
   - **触发时机**：
     - L1 缓冲总结完成后：更新知识图谱节点访问频率和边权重
     - L2 记忆总结完成后：更新记忆访问频率
   - **更新内容**：
     - 访问频率（access_count）
     - 最近访问时间（last_access_time）
     - 图谱边权重（基于互动频率）
   - 实现位置：`summarizer.py`、`memory_retriever.py`

---

## 待办事项

### Config 模块

- [ ] **插件主类实现**：`iris_memory/__init__.py` 需实现 `IrisTierMemoryPlugin` 类
  - 继承 `Star` 类
  - 在 `__init__` 中调用 `context.get_data_dir()` 获取数据目录
  - 调用 `init_config(config, data_dir)` 初始化配置系统
  - 参考文档第 735-746 行的示例代码

- [ ] **配置路径实际调用**：验证 `context.get_data_dir()` 是否正确返回 AstrBot 管理的数据目录
