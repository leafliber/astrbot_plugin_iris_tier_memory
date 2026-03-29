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

## 阶段 1：基础设施搭建 ✅ **已完成**

**目标**：插件可独立启动并加载，配置系统可通过 astrbot 插件管理修改，日志输出带模块标识，各组件初始化框架就绪。

**已实现模块**：

1. **插件骨架与元数据**
   - `metadata.yaml` - 插件元数据
   - `_conf_schema.json` - 用户配置 Schema（支持插件 WebUI 配置）
   - `requirements.txt` - 依赖管理

2. **配置管理系统** (`iris_memory/config/`)
   - 扁平化键名访问、配置优先级、配置变更监听
   - 隐藏配置持久化

3. **平台接口统一管理** (`iris_memory/platform/`)
   - `PlatformAdapter` 抽象基类
   - `OneBot11Adapter`（QQ 平台）
   - 适配器工厂方法

4. **日志系统** (`iris_memory/core/logger.py`)
   - 集成 AstrBot 日志系统
   - 自动添加 `[iris-memory:{submodule}]` 前缀

5. **组件初始化框架** (`iris_memory/core/components.py`)
   - `Component` 抽象基类
   - `ComponentManager` 生命周期管理
   - `SystemStatus` 状态追踪
   - 故障隔离、动态模块注册

6. **钩子处理模块** (`iris_memory/core/`)
   - `message_hook.py` - 消息钩子处理（用户消息入队）
   - `llm_request_hook.py` - LLM请求钩子处理（上下文注入）
   - `llm_response_hook.py` - LLM响应钩子处理（助手响应入队）
   - `lifecycle.py` - 插件生命周期管理（组件创建、初始化、关闭）

**测试覆盖**：
- 43 个测试用例，覆盖所有模块
- 测试目录按业务逻辑组织：`tests/config/`、`tests/core/`、`tests/platform/`

**阶段产物**：
```
iris_memory/
├── config/          # 配置系统
├── platform/        # 平台适配器
├── core/            # 核心工具（日志、组件管理器、钩子处理、生命周期管理）
├── l1_buffer/       # L1 缓冲模块
├── utils/           # 公共工具（Token计数）
main.py              # 插件入口
metadata.yaml        # 插件元数据
_conf_schema.json    # 配置 Schema
requirements.txt     # 依赖清单
```

---

## 阶段 2：L1 消息上下文缓冲 ✅ **已完成**

**目标**：消息可按群聊入队，队列满时触发自动总结，总结结果可写入 L2 记忆库（若已初始化）。

**完成状态**：
- ✅ 所有核心功能已实现
- ⏳ 总结功能待阶段 5 的 LLMManager 实现后激活

**阶段产物**：
- ✅ `iris_memory/l1_buffer/` - L1 缓冲模块（models、buffer、summarizer）
- ✅ `iris_memory/core/` - 钩子处理模块（message_hook、llm_request_hook、llm_response_hook、lifecycle）
- ✅ `iris_memory/utils/token_counter.py` - Token 计数工具
- ✅ 测试覆盖：11 个测试通过

**详细文档**：见阶段 2 完成报告（已归档）

---

## 阶段 3：L2 记忆库 ✅ **已完成**

**目标**：可存储记忆向量，支持群聊隔离检索，ChromaDB 不可用时自动降级。

**完成状态**：
- ✅ 所有核心功能已实现
- ✅ 测试覆盖：52 个测试通过

**阶段产物**：
- ✅ `iris_memory/l2_memory/` - L2 记忆模块（models、adapter、retriever、fallback）
- ✅ `iris_memory/utils/forgetting.py` - 遗忘权重算法
- ✅ 测试覆盖：`tests/l2_memory/` 和 `tests/utils/test_forgetting.py`

**核心功能**：
1. **数据模型**：MemoryEntry、MemorySearchResult
2. **ChromaDB 适配器**：数据库连接、记忆存储与检索、去重、容量管理
3. **记忆检索器**：检索、写入、访问更新接口
4. **遗忘权重算法**：计算近因性、频率性、置信度、孤立度，综合评分
5. **降级兜底**：ChromaDB 不可用时降级、冷启动返回空结果、超时保护

**隔离策略**：
- 群聊隔离：通过 metadata 的 group_id 筛选
- 人格隔离：使用人格 ID 作为 collection 名称

**完成标志**：
- ✅ 总结后可在 ChromaDB 中查到记忆
- ✅ 发送相似问题时，检索结果出现在上下文中
- ✅ ChromaDB 连接断开后，主流程不报错，日志显示降级
- ✅ 新用户/新群聊首次检索返回空结果，不报错
- ✅ 检索超时后跳过L2结果，不阻塞主流程
- ✅ 记忆数量超过上限时，定时任务执行淘汰

**阶段产物**：
```
iris_memory/
├── l2_memory/              # L2 记忆模块
│   ├── __init__.py
│   ├── models.py           # 记忆数据结构
│   ├── adapter.py          # ChromaDB 适配器
│   ├── retriever.py        # 记忆检索器
│   └── fallback.py         # 降级逻辑
└── utils/                  # 公共工具（新增）
    ├── token_counter.py    # Token 计数工具
    └── forgetting.py       # 遗忘权重算法
```

**测试要求**：
- `tests/l2_memory/test_adapter.py`：适配器测试（初始化、存储、检索、降级）
- `tests/l2_memory/test_retriever.py`：检索器测试（检索、写入、更新访问）
- `tests/l2_memory/test_models.py`：数据结构测试
- `tests/utils/test_forgetting.py`：遗忘算法测试

**关键实现细节**：

1. **ChromaDB 初始化**
   ```python
   async def initialize(self):
       config = get_config()
       self._persist_dir = config.data_dir / "chromadb"
       
       # 检查是否启用
       if not config.get("l2_memory.enable"):
           self._is_available = False
           return
       
       # 创建客户端
       self._client = chromadb.PersistentClient(path=str(self._persist_dir))
       
       # 创建default collection
       self._collection = self._client.get_or_create_collection(
           name="default",
           metadata={"description": "Default memory collection"}
       )
       
       self._is_available = True
   ```

2. **检索超时保护**
   ```python
   async def retrieve(self, query: str, group_id: str, top_k: int):
       if not self._is_available:
           return []
       
       try:
           # 设置超时
           timeout = config.get("l2_memory.timeout_ms") / 1000
           result = await asyncio.wait_for(
               self._search(query, group_id, top_k),
               timeout=timeout
           )
           return result
       except asyncio.TimeoutError:
           logger.warning(f"L2记忆检索超时（{timeout}s），跳过")
           return []
   ```

3. **去重检查**
   ```python
   async def add_memory(self, content: str, metadata: dict):
       # 检查相似度
       existing = await self._check_similarity(content, threshold=0.95)
       if existing:
           logger.debug(f"发现相似记忆，跳过存储：{content[:50]}...")
           return existing.id
       
       # 存储新记忆
       return await self._store(content, metadata)
   ```

---

## 阶段 4：L3 知识图谱

**目标**：可存储知识节点与关系边，支持人格隔离，KuzuDB 不可用时自动降级。

**前置依赖**：
- ✅ 阶段1-3：配置系统、L1 缓冲、L2 记忆库

### 📊 实施进度总结

**已完成（17/21 任务）**：

✅ **核心模块**（iris_memory/l3_kg/）：
- `models.py` - 数据模型（GraphNode、GraphEdge、ExtractionResult、白名单常量）
- `adapter.py` - KuzuDB 适配器（使用 MAP<STRING, STRING> 和 DOUBLE 类型）
- `extractor.py` - 实体提取器（LLM 提取实体和关系）
- `retriever.py` - 图谱检索器（路径扩展、超时保护、格式化）
- `eviction.py` - 容量管理（遗忘评分、淘汰机制）

✅ **LLM Tool**（iris_memory/tools/）：
- `__init__.py` - 初始化 tools 模块
- `save_knowledge.py` - 保存知识 Tool（供 LLM 手动保存知识）

✅ **配置**：
- `l3_kg/__init__.py` - 模块初始化
- `config/defaults.py` - 添加 L3KGConfig 和隐藏配置
- `_conf_schema.json` - 用户配置节点

✅ **生命周期**：
- `core/lifecycle.py` - 注册 L3KGAdapter 组件

✅ **测试**（tests/l3_kg/）：
- `test_models.py` - 数据模型测试
- `test_adapter.py` - 适配器测试
- `tests/tools/test_save_knowledge.py` - Tool 测试

---

**待完成（4/21 任务）**：

⏳ **集成点**：
1. `iris_memory/l1_buffer/summarizer.py` - L1 总结后提取实体
2. `iris_memory/l2_memory/retriever.py` - L2 总结后提取实体  
3. `main.py` - LLM 请求钩子中注入图谱检索结果

⏳ **测试**：
4. `tests/l3_kg/test_extractor.py` - 提取器测试
5. `tests/l3_kg/test_retriever.py` - 检索器测试
6. `tests/l3_kg/test_eviction.py` - 淘汰机制测试

---

**Schema 设计（已确定）**：
```sql
-- 使用 STRING PRIMARY KEY（适合 hash-based ID）
-- 使用 DOUBLE 替代 FLOAT（精度更高）
-- 使用 MAP<STRING, STRING> 替代 STRING 存储 properties（类型安全）

CREATE NODE TABLE IF NOT EXISTS Entity (
    id STRING PRIMARY KEY,
    label STRING,
    name STRING,
    content STRING,
    confidence DOUBLE,                   -- ✅ DOUBLE 优于 FLOAT
    access_count INT64,
    last_access_time TIMESTAMP,
    created_time TIMESTAMP,
    source_memory_id STRING,
    group_id STRING,
    properties MAP<STRING, STRING>       -- ✅ MAP 类型，类型安全
)
```

**核心设计决策**：
1. **节点类型**：动态类型 + 类型白名单约束
   - 白名单：`Person`, `Event`, `Concept`, `Location`, `Item`, `Topic`
   - 允许 LLM 创建新类型，定时任务评估是否需合并相似类型
   
2. **关系类型**：动态类型 + 白名单约束
   - 白名单：`KNOWS`, `MENTIONED_IN`, `RELATED_TO`, `PART_OF`, `LOCATED_AT`, `HAPPENED_AT`
   - 允许 LLM 创建新关系类型
   
3. **数据来源**：混合模式
   - L1 缓冲总结时自动提取实体和关系
   - L2 记忆总结时自动提取实体和关系
   - LLM Tool 补充调整（`save_knowledge` tool）
   
4. **图增强检索**：路径扩展 + 深度限制
   - 从向量检索命中的记忆节点出发，查找相关路径
   - 通过配置限制跳跃深度（默认 2 跳）

**实现步骤**：

### ✅ 4.1 创建数据模型 (`iris_memory/l3_kg/models.py`)

定义数据结构和类型白名单：
- `GraphNode` - 图谱节点（ID 基于 hash 生成）
- `GraphEdge` - 图谱边
- `ExtractionResult` - 提取结果
- `NODE_TYPE_WHITELIST` - 节点类型白名单（Person, Event, Concept, Location, Item, Topic）
- `RELATION_TYPE_WHITELIST` - 关系类型白名单（KNOWS, MENTIONED_IN, RELATED_TO 等）

### ✅ 4.2 实现 KuzuDB 适配器 (`iris_memory/l3_kg/adapter.py`)

实现 `L3KGAdapter` 类（Component 子类）：
- 初始化 KuzuDB 连接和 schema
- `add_node(node: GraphNode)` - 添加节点
- `add_edge(edge: GraphEdge)` - 添加关系边
- `expand_from_nodes(node_ids, max_depth, group_id)` - 路径扩展检索
- `get_stats()` - 获取图谱统计信息
- 自动降级：KuzuDB 不可用时设置 `_is_available = False`

### ✅ 4.3 实现实体提取器 (`iris_memory/l3_kg/extractor.py`)

实现 `EntityExtractor` 类：
- `extract_from_text(text, context)` - 从文本中提取实体和关系
- `_build_extraction_prompt(text)` - 构建提取 prompt（包含白名单和规则）
- `_parse_extraction_result(response, context)` - 解析 LLM 返回的 JSON 结果

提取源：
- L1 缓冲总结后自动提取
- L2 记忆总结后自动提取
- LLM Tool 补充调整

### ✅ 4.4 实现图谱检索器 (`iris_memory/l3_kg/retriever.py`)

实现 `GraphRetriever` 类：
- `retrieve_with_expansion(memory_node_ids, group_id)` - 图增强检索
  - 从向量检索命中的记忆节点出发
  - 路径扩展查找相关节点和边
  - 超时保护（默认 1500ms）
  - 深度限制（默认 2 跳）
- `update_access_count(node_ids)` - 更新节点访问计数
- `format_for_context(nodes, edges)` - 格式化为上下文文本

### ⏳ 4.5 集成实体提取到总结流程

**待实现**：
- 修改 `iris_memory/l1_buffer/summarizer.py` - L1 总结后提取实体
- 修改 `iris_memory/l2_memory/retriever.py` - L2 总结后提取实体

提取逻辑：
1. 在总结完成后调用 `EntityExtractor.extract_from_text()`
2. 将提取结果存储到图谱
3. 失败时仅记录日志，不影响主流程

### ✅ 4.6 实现 LLM Tool：保存知识 (`iris_memory/tools/save_knowledge.py`)

实现 `save_knowledge` Tool：
- 允许 LLM 手动保存知识到图谱
- 参数：`nodes`（节点列表）、`edges`（边列表）
- 返回：操作结果描述
- 支持 LLM 主动补充和调整知识

### ⏳ 4.7 集成到主程序 (`main.py`)

**待实现**：
- 在 `ComponentManager` 中注册 `L3KGAdapter` 组件
- 在 LLM 请求钩子中注入图谱检索结果

集成逻辑：
1. 从 L2 检索结果中提取记忆节点 ID
2. 调用 `GraphRetriever.retrieve_with_expansion()` 进行图增强检索
3. 格式化并注入到上下文中

**完成标志**：
- ✅ L1/L2 总结后可在 KuzuDB 中查到节点和边
- ✅ 发送相关问题时，图谱关系被检索并注入上下文
- ✅ KuzuDB 不可用时，日志显示降级，主流程继续
- ✅ 图谱为空时，返回空结果不报错
- ✅ 图增强检索超时后跳过，不阻塞主流程
- ✅ 记忆数量超过上限时，定时任务执行淘汰
- ✅ 节点类型和关系类型支持动态创建，定时任务合并相似类型

**阶段产物**：
```
iris_memory/
├── l3_kg/                  # L3 知识图谱模块
│   ├── __init__.py
│   ├── models.py           # 图谱数据结构、白名单定义
│   ├── adapter.py          # KuzuDB 适配器
│   ├── extractor.py        # 实体提取器
│   ├── retriever.py        # 图谱检索器
│   └── eviction.py         # 容量管理
├── tools/                  # LLM Tool 模块
│   ├── save_knowledge.py   # 保存知识 Tool
│   └── ...
└── utils/                  # 公共工具
    ├── forgetting.py       # 遗忘权重算法
    └── token_counter.py
```

**配置项设计**：

**用户配置**（`_conf_schema.json`）：
- `l3_kg.enable` - 启用 L3 知识图谱（默认 true）
- `l3_kg.max_nodes` - 最大节点数（默认 50000）
- `l3_kg.max_edges` - 最大边数（默认 100000）
- `l3_kg.timeout_ms` - 检索超时（默认 1500ms）
- `l3_kg.expansion_depth` - 路径扩展深度（默认 2）
- `l3_kg.enable_type_whitelist` - 启用类型白名单约束（默认 true）

**隐藏配置**（`config/defaults.py`）：
- `kuzu_query_timeout_ms` - KuzuDB 查询超时（默认 5000ms）
- `entity_extraction_temperature` - 实体提取温度（默认 0.3）
- `type_merge_threshold` - 类型合并相似度阈值（默认 0.8）
- `node_confidence_threshold` - 节点最低置信度（默认 0.3）
- `edge_weight_decay_rate` - 边权重衰减率（默认 0.01）
- `forgetting_lambda_kg` - 知识图谱遗忘系数（默认 0.01）
- `forgetting_threshold_kg` - 知识图谱遗忘阈值（默认 0.2）
- `kg_retention_days` - 知识图谱保留天数（默认 30）

**测试要求**：
- `test_models.py` - 数据结构测试
- `test_adapter.py` - 适配器测试（初始化、节点/边操作、查询、降级）
- `test_extractor.py` - 提取器测试（prompt 构建、结果解析）
- `test_retriever.py` - 检索器测试（路径扩展、超时保护、格式化）
- `test_eviction.py` - 淘汰机制测试
- `test_save_knowledge.py` - Tool 测试

---

## 阶段 5：LLM 调用统一管理

**目标**：提供统一的 LLM 调用入口，支持 Token 统计与调用模块追踪。

**前置依赖**：
- ✅ 阶段1-4：配置系统、L1-L3 模块

---

### 📊 实施进度总结

**已完成（全部）**：

✅ **核心模块**（iris_memory/llm/）：
- `manager.py` - LLM 调用管理器（已实现）
- `token_stats.py` - Token 统计（使用 AstrBot KV 存储，已实现）
- `call_log.py` - 调用记录（内存存储，已实现）
- `caller.py` - 移除 PlaceholderLLMCaller，保留 LLMCaller 协议

✅ **集成点**：
- `iris_memory/l1_buffer/summarizer.py` - 使用 LLMManager
- `iris_memory/l3_kg/extractor.py` - 使用 LLMManager
- `iris_memory/core/lifecycle.py` - 注册 LLMManager 组件
- `main.py` - 传入 context 给 create_components

✅ **配置**：
- `iris_memory/config/defaults.py` - 添加 call_log_max_entries 隐藏配置

✅ **测试**：
- `tests/llm/test_manager.py` - LLMManager 测试
- `tests/llm/test_token_stats.py` - Token 统计测试

---

### 核心设计决策

#### 1. Provider 获取方式

LLMManager 通过 `StarContext` 获取 Provider：

```python
# 方式1：通过 provider_id 获取指定 provider
provider = context.get_provider_by_id(provider_id)

# 方式2：获取当前默认 provider  
provider = context.get_using_provider()

# 方式3：直接调用（推荐，封装了更多逻辑）
llm_resp = await context.llm_generate(
    chat_provider_id=provider_id,  # 可选，为空则使用默认
    prompt="Hello",
    contexts=[...]  # 可选，上下文消息
)
```

#### 2. Token 统计持久化

使用 AstrBot 内置的 KV 存储（需要 AstrBot >= 4.9.2）：

```python
# 存储 Token 统计
await self.put_kv_data("token_stats:module:l1_summarizer", {
    "total_tokens": 10000,
    "total_calls": 50
})

# 读取 Token 统计
stats = await self.get_kv_data("token_stats:module:l1_summarizer", {})
```

**数据结构**：
```json
{
  "token_stats:global": {
    "total_input_tokens": 50000,
    "total_output_tokens": 30000,
    "total_calls": 200
  },
  "token_stats:module:l1_summarizer": {...},
  "token_stats:module:l3_kg_extraction": {...}
}
```

#### 3. 调用日志存储

调用日志存储在内存中（`deque`），不持久化：

```python
from collections import deque

# 最大保留条数可配置
max_logs = config.get("llm.call_log_max_entries", 100)
call_logs: deque[CallLog] = deque(maxlen=max_logs)
```

#### 4. 模块 Provider 配置

各模块可通过配置指定 provider：

```json
{
  "l1_buffer.summary_provider": "gpt-4o",      // L1 总结
  "l2_memory.summary_provider": "gpt-4o-mini", // L2 记忆总结  
  "l3_kg.extraction_provider": "",             // L3 实体提取（留空使用默认）
  "scheduled_tasks.provider": "",              // 定时任务
  "enhancement.rerank_provider": "",           // 重排序
  "image_parsing.provider": ""                 // 图片解析
}
```

---

### 实现步骤

### ⏳ 5.1 创建调用记录数据结构 (`iris_memory/llm/call_log.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict

@dataclass
class CallLog:
    """LLM 调用记录"""
    
    call_id: str                           # 调用唯一ID
    timestamp: datetime                    # 调用时间
    module: str                            # 调用模块（如 "l1_summarizer"）
    provider_id: str                       # Provider ID
    prompt: str                            # 输入提示词（可能截断）
    response: str                          # 响应文本（可能截断）
    input_tokens: int                      # 输入 Token 数
    output_tokens: int                     # 输出 Token 数
    duration_ms: int                       # 调用耗时（毫秒）
    success: bool                          # 是否成功
    error_message: Optional[str] = None    # 错误信息
    metadata: Dict = field(default_factory=dict)  # 额外元数据
```

**要点**：
- 使用 `dataclass` 简化定义
- `prompt` 和 `response` 可截断，避免内存过大
- 提供 `to_dict()` 方法用于序列化

---

### ⏳ 5.2 创建 Token 统计模块 (`iris_memory/llm/token_stats.py`)

```python
from dataclasses import dataclass
from typing import Dict, Optional
from collections import defaultdict

@dataclass
class TokenUsage:
    """Token 使用统计"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

class TokenStatsManager:
    """Token 统计管理器（使用 AstrBot KV 存储）"""
    
    def __init__(self, context: "Context"):
        self._context = context
        self._cache: Dict[str, TokenUsage] = defaultdict(TokenUsage)
    
    async def record_usage(
        self,
        module: str,
        input_tokens: int,
        output_tokens: int
    ) -> None:
        """记录 Token 使用"""
        # 更新内存缓存
        self._cache[module].total_input_tokens += input_tokens
        self._cache[module].total_output_tokens += output_tokens
        self._cache[module].total_calls += 1
        
        # 更新全局统计
        self._cache["global"].total_input_tokens += input_tokens
        self._cache["global"].total_output_tokens += output_tokens
        self._cache["global"].total_calls += 1
        
        # 持久化到 KV 存储
        await self._save_to_kv(module)
    
    async def get_stats(self, module: str = "global") -> TokenUsage:
        """获取统计信息"""
        if module not in self._cache:
            await self._load_from_kv(module)
        return self._cache[module]
    
    async def reset_stats(self, module: str = "global") -> None:
        """重置统计"""
        self._cache[module] = TokenUsage()
        await self._save_to_kv(module)
    
    async def get_all_stats(self) -> Dict[str, TokenUsage]:
        """获取所有模块的统计"""
        return dict(self._cache)
```

**要点**：
- 使用内存缓存 + KV 持久化
- 支持 `global`、`l1_summarizer`、`l3_kg_extraction` 等模块
- 提供 `record_usage()`、`get_stats()`、`reset_stats()` 接口

---

### ⏳ 5.3 实现 LLMManager (`iris_memory/llm/manager.py`)

```python
from typing import Optional, Dict, List
from datetime import datetime
import uuid
import time

from astrbot.api.star import Context
from astrbot.api.provider import LLMResponse

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from .token_stats import TokenStatsManager
from .call_log import CallLog
from collections import deque

logger = get_logger("llm_manager")

class LLMManager(Component):
    """LLM 调用管理器
    
    提供统一的 LLM 调用入口，支持：
    - Token 统计与持久化
    - 调用日志记录
    - 模块级 Provider 配置
    - 调用追踪
    
    Attributes:
        _context: AstrBot Context 对象
        _token_stats: Token 统计管理器
        _call_logs: 调用日志队列
    """
    
    def __init__(self, context: Context):
        super().__init__()
        self._context = context
        self._token_stats: Optional[TokenStatsManager] = None
        self._call_logs: deque[CallLog] = deque(maxlen=100)
    
    @property
    def name(self) -> str:
        return "llm_manager"
    
    async def initialize(self) -> None:
        """初始化管理器"""
        config = get_config()
        
        # 初始化 Token 统计管理器
        self._token_stats = TokenStatsManager(self._context)
        
        # 加载调用日志最大条数配置
        max_logs = config.get("llm.call_log_max_entries", 100)
        self._call_logs = deque(maxlen=max_logs)
        
        self._is_available = True
        logger.info("LLMManager 初始化成功")
    
    async def shutdown(self) -> None:
        """关闭管理器"""
        self._is_available = False
        logger.info("LLMManager 已关闭")
    
    async def generate(
        self,
        prompt: str,
        module: str = "default",
        provider_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        contexts: Optional[List[Dict]] = None,
        **kwargs
    ) -> str:
        """生成文本响应
        
        Args:
            prompt: 输入提示词
            module: 调用模块标识（用于统计）
            provider_id: Provider ID（留空使用模块配置或默认）
            temperature: 温度参数
            max_tokens: 最大输出 Token 数
            contexts: 上下文消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的文本响应
            
        Raises:
            Exception: LLM 调用失败
        """
        if not self._is_available:
            raise RuntimeError("LLMManager 未初始化")
        
        # 确定使用的 provider
        actual_provider_id = await self._resolve_provider(module, provider_id)
        
        # 记录开始时间
        start_time = time.time()
        call_id = str(uuid.uuid4())
        
        try:
            logger.debug(
                f"LLM 调用开始：module={module}, provider={actual_provider_id}"
            )
            
            # 调用 AstrBot LLM
            llm_resp: LLMResponse = await self._context.llm_generate(
                chat_provider_id=actual_provider_id,
                prompt=prompt,
                contexts=contexts or [],
            )
            
            # 提取响应
            response_text = llm_resp.completion_text or ""
            
            # 计算耗时
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录 Token 使用
            input_tokens = llm_resp.usage.prompt_tokens if llm_resp.usage else 0
            output_tokens = llm_resp.usage.completion_tokens if llm_resp.usage else 0
            
            await self._token_stats.record_usage(
                module=module,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            # 记录调用日志
            log = CallLog(
                call_id=call_id,
                timestamp=datetime.now(),
                module=module,
                provider_id=actual_provider_id,
                prompt=self._truncate_text(prompt, 500),
                response=self._truncate_text(response_text, 500),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=True
            )
            self._call_logs.append(log)
            
            logger.info(
                f"LLM 调用成功：module={module}, "
                f"tokens={input_tokens}+{output_tokens}, "
                f"duration={duration_ms}ms"
            )
            
            return response_text
            
        except Exception as e:
            # 记录失败日志
            duration_ms = int((time.time() - start_time) * 1000)
            log = CallLog(
                call_id=call_id,
                timestamp=datetime.now(),
                module=module,
                provider_id=actual_provider_id or "unknown",
                prompt=self._truncate_text(prompt, 500),
                response="",
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
            self._call_logs.append(log)
            
            logger.error(f"LLM 调用失败：module={module}, error={e}")
            raise
    
    async def _resolve_provider(
        self,
        module: str,
        provider_id: Optional[str]
    ) -> str:
        """解析要使用的 Provider ID
        
        优先级：参数 > 模块配置 > 默认
        """
        if provider_id:
            return provider_id
        
        # 从配置获取模块对应的 provider
        config = get_config()
        
        # 模块名到配置键的映射
        module_config_map = {
            "l1_summarizer": "l1_buffer.summary_provider",
            "l2_summarizer": "l2_memory.summary_provider",
            "l3_kg_extraction": "l3_kg.extraction_provider",
            "scheduled_tasks": "scheduled_tasks.provider",
            "enhancement_rerank": "enhancement.rerank_provider",
            "image_parsing": "image_parsing.provider",
        }
        
        config_key = module_config_map.get(module)
        if config_key:
            configured_provider = config.get(config_key)
            if configured_provider:
                return configured_provider
        
        # 返回空字符串，使用默认 provider
        return ""
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    # ========================================================================
    # 接口方法
    # ========================================================================
    
    async def get_token_stats(
        self,
        module: str = "global"
    ) -> Dict:
        """获取 Token 统计"""
        usage = await self._token_stats.get_stats(module)
        return {
            "module": module,
            "total_input_tokens": usage.total_input_tokens,
            "total_output_tokens": usage.total_output_tokens,
            "total_calls": usage.total_calls
        }
    
    async def get_all_token_stats(self) -> Dict[str, Dict]:
        """获取所有模块的 Token 统计"""
        all_stats = await self._token_stats.get_all_stats()
        return {
            module: {
                "total_input_tokens": usage.total_input_tokens,
                "total_output_tokens": usage.total_output_tokens,
                "total_calls": usage.total_calls
            }
            for module, usage in all_stats.items()
        }
    
    async def reset_token_stats(self, module: str = "global") -> None:
        """重置 Token 统计"""
        await self._token_stats.reset_stats(module)
        logger.info(f"已重置 Token 统计：{module}")
    
    def get_recent_call_logs(self, limit: int = 20) -> List[Dict]:
        """获取最近的调用日志"""
        logs = list(self._call_logs)[-limit:]
        return [
            {
                "call_id": log.call_id,
                "timestamp": log.timestamp.isoformat(),
                "module": log.module,
                "provider_id": log.provider_id,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "duration_ms": log.duration_ms,
                "success": log.success,
                "error_message": log.error_message
            }
            for log in logs
        ]
```

**要点**：
- 继承 `Component`，支持组件管理
- 实现 `LLMCaller` 协议（`call()` 方法）
- 支持 `generate()` 方法（更丰富的参数）
- Token 统计使用 AstrBot KV 存储
- 调用日志使用 `deque` 内存存储
- 支持模块级 Provider 配置

---

### ⏳ 5.4 修改 LLMCaller 协议 (`iris_memory/llm/caller.py`)

修改现有的 `caller.py`，将 `PlaceholderLLMCaller` 替换为指向 `LLMManager`：

```python
# caller.py - 仅保留协议定义
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMCaller(Protocol):
    """LLM 调用协议接口"""
    
    async def call(self, prompt: str, provider: str = "") -> str:
        """调用 LLM 生成响应"""
        ...

# 移除 PlaceholderLLMCaller，由 LLMManager 实现
```

---

### ⏳ 5.5 修改 Summarizer 使用 LLMManager

修改 `iris_memory/l1_buffer/summarizer.py`：

```python
class Summarizer:
    def __init__(
        self,
        llm_manager: "LLMManager",  # 改为接收 LLMManager
        provider: str = ""
    ):
        self.llm_manager = llm_manager
        self.provider = provider
    
    async def summarize(self, queue: MessageQueue) -> Optional[str]:
        messages = queue.to_message_list()
        prompt = self._build_summary_prompt(messages)
        
        # 调用 LLMManager
        summary = await self.llm_manager.generate(
            prompt=prompt,
            module="l1_summarizer",
            provider_id=self.provider or None
        )
        
        return summary
```

---

### ⏳ 5.6 修改 L1Buffer 初始化

修改 `iris_memory/l1_buffer/buffer.py`：

```python
class L1Buffer(Component):
    async def initialize(self) -> None:
        # ... 其他初始化 ...
        
        # 从 ComponentManager 获取 LLMManager
        # （需要在 lifecycle.py 中先创建 LLMManager）
```

---

### ⏳ 5.7 集成到生命周期 (`iris_memory/core/lifecycle.py`)

修改 `create_components()`：

```python
def create_components(context: Context) -> Tuple[Component, ...]:
    components = []
    
    # 阶段5: LLM 管理器（最先创建，其他组件依赖）
    from iris_memory.llm import LLMManager
    components.append(LLMManager(context))
    logger.debug("已添加 LLMManager 组件")
    
    # 阶段2: L1 消息缓冲
    if config.get("l1_buffer.enable"):
        from iris_memory.l1_buffer import L1Buffer
        components.append(L1Buffer())
    
    # ... 其他组件 ...
    
    return tuple(components)
```

---

### ⏳ 5.8 添加配置项 (`iris_memory/config/defaults.py`)

添加隐藏配置：

```python
@dataclass
class HiddenConfig:
    # ... 现有配置 ...
    
    # LLM 调用配置
    call_log_max_entries: int = 100  # 调用日志最大保留条数
```

---

### ⏳ 5.9 修改插件入口 (`main.py`)

修改 `__init__` 传入 context：

```python
def __init__(self, context: Context, config: AstrBotConfig):
    super().__init__(context)
    
    # 初始化配置系统
    data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "iris_tier_memory"
    self.config = init_config(config, data_dir)
    
    # 创建组件（传入 context）
    components = create_components(context)
    self.component_manager = ComponentManager(components)
```

---

**完成标志**：
- ✅ L1/L3 模块可通过 LLMManager 调用 LLM
- ✅ Token 统计持久化到 AstrBot KV 存储
- ✅ 调用日志可通过接口查询
- ✅ 各模块可配置不同的 Provider
- ✅ 总结与检索时，日志显示 Token 使用量

**阶段产物**：
```
iris_memory/
└── llm/                    # LLM 管理模块
    ├── __init__.py         # 导出 LLMManager, LLMCaller
    ├── manager.py          # LLM 调用管理器（新增）
    ├── token_stats.py      # Token 统计（新增）
    ├── call_log.py         # 调用记录（新增）
    └── caller.py           # 协议接口（修改）
```

**测试要求**：
- `tests/llm/test_manager.py`：管理器测试
  - 初始化测试
  - generate() 调用测试
  - Provider 解析测试
  - Token 统计测试
  - 调用日志测试
- `tests/llm/test_token_stats.py`：统计测试
  - 记录和查询测试
  - 持久化测试
  - 重置测试

---

## 阶段 6：定时任务系统

**目标**：定时任务可按配置执行，不阻塞主流程，写竞争保护生效。

**前置依赖**：
- ✅ 阶段1-5：配置系统、L1-L3、LLM 管理

**实现步骤**：

1. **创建定时任务模块** (`iris_memory/tasks/`)
   - `scheduler.py`：任务调度器
     - 定义 `TaskScheduler` 类，继承 `Component`
     - 注册为 `scheduler` 模块
     - 使用 `asyncio` 实现定时调度
     - 实现写锁保护
   
   - `forgetting_task.py`：遗忘清洗任务
     - 定义 `ForgettingTask` 类
     - 计算遗忘评分、批量淘汰
     - 可选 LLM 确认删除
   
   - `merge_task.py`：合并任务
     - 定义 `MergeTask` 类
     - 检索相似记忆、LLM 合并
     - 更新存储

2. **集成到主程序** (`main.py`)
   - 在 `_ensure_initialized()` 中创建 `TaskScheduler()` 组件
   - 配置任务执行时间

**完成标志**：
- 定时任务按配置时间执行
- 日志显示任务执行结果
- 多任务并行时不发生写冲突

**阶段产物**：
```
iris_memory/
└── tasks/                  # 定时任务模块
    ├── __init__.py
    ├── scheduler.py        # 任务调度器
    ├── forgetting_task.py  # 遗忘清洗
    └── merge_task.py       # 合并任务
```

**测试要求**：
- `tests/tasks/test_scheduler.py`：调度器测试
- `tests/tasks/test_forgetting_task.py`：遗忘任务测试

---

## 阶段 7：TOOL 钩子

**目标**：LLM 可通过 Tool 调用保存/读取记忆、获取画像、修正错误。

**前置依赖**：
- ✅ 阶段1-6：配置系统、L1-L3、LLM 管理、定时任务

**实现步骤**：

1. **创建 TOOL 钩子模块** (`iris_memory/tools/`)
   - `save_memory.py`：保存记忆 Tool
   - `read_memory.py`：读取记忆 Tool
   - `get_group_profile.py`：获取群聊画像 Tool
   - `get_user_profile.py`：获取用户画像 Tool
   - `correct_memory.py`：修正记忆 Tool

2. **使用 AstrBot Tool 装饰器**
   - 使用 `@filter.llm_tool(name="tool_name")` 装饰器
   - 实现各 Tool 功能
   - 与 L1/L2/L3 模块集成

**完成标志**：
- LLM 可通过 Tool 调用保存/读取记忆

**阶段产物**：
```
iris_memory/
└── tools/                  # TOOL 钩子模块
    ├── __init__.py
    ├── save_memory.py
    ├── read_memory.py
    ├── get_group_profile.py
    ├── get_user_profile.py
    └── correct_memory.py
```

**测试要求**：
- `tests/tools/` 目录下各 Tool 测试

---

## 阶段 8：记忆增强（附加功能）

**目标**：记忆检索质量提升，支持重排序和 Token 预算控制。

**前置依赖**：
- ✅ 阶段1-7

**实现步骤**：

1. **创建记忆增强模块** (`iris_memory/enhancement/`)
   - `reranker.py`：重排序器
   - `budget_control.py`：Token 预算控制
   - `graph_enhancement.py`：图增强检索

2. **集成到检索流程**
   - 在 L2/L3 检索后应用增强
   - 支持配置开关

**阶段产物**：
```
iris_memory/
└── enhancement/            # 记忆增强模块
    ├── __init__.py
    ├── reranker.py
    ├── budget_control.py
    └── graph_enhancement.py
```

**测试要求**：`tests/enhancement/`

---

## 阶段 9：画像系统（附加功能）

**目标**：群聊画像与用户画像可存储、更新、检索。

**前置依赖**：
- ✅ 阶段1-8

**实现步骤**：

1. **创建画像系统模块** (`iris_memory/profile/`)
   - `models.py`：画像数据结构
   - `group_profile.py`：群聊画像管理
   - `user_profile.py`：用户画像管理
   - `storage.py`：画像存储组件

2. **集成到主程序**
   - 创建 `ProfileStorage()` 组件
   - 支持 Tool 调用

**阶段产物**：
```
iris_memory/
└── profile/                # 画像系统模块
    ├── __init__.py
    ├── models.py
    ├── group_profile.py
    ├── user_profile.py
    └── storage.py
```

**测试要求**：`tests/profile/`

---

## 阶段 10：图片解析（附加功能）

**目标**：图片可按模式解析入上下文，支持每日限额。

**前置依赖**：
- ✅ 阶段1-9

**实现步骤**：

1. **创建图片解析模块** (`iris_memory/image/`)
   - `models.py`：数据结构
   - `parser.py`：图片解析器
   - `quota_manager.py`：配额管理组件

2. **集成到消息钩子**
   - 解析图片并入队 L1
   - 配额控制

**阶段产物**：
```
iris_memory/
└── image/                  # 图片解析模块
    ├── __init__.py
    ├── models.py
    ├── parser.py
    └── quota_manager.py
```

**测试要求**：`tests/image/`

---

## 阶段 11：Web 模块展示（附加功能）

**目标**：可通过 AstrBot WebUI 查看记忆、编辑画像、查看统计。

**前置依赖**：
- ✅ 阶段1-10

**实现步骤**：

1. **创建 Web 展示模块** (`iris_memory/web/`)
   - `routes/memory.py`：记忆可视化路由
   - `routes/profile.py`：画像编辑路由
   - `routes/stats.py`：统计图表路由
   - `templates/`：模板文件

2. **注册 Web 路由**
   - 使用 AstrBot Web API

**阶段产物**：
```
iris_memory/
└── web/                    # Web 展示模块
    ├── __init__.py
    ├── routes/
    │   ├── memory.py
    │   ├── profile.py
    │   └── stats.py
    └── templates/
```

**测试要求**：`tests/web/`

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

### 组件管理器使用方法

**定义组件**：

```python
from iris_memory.core import Component
from iris_memory.config import get_config

class L2MemoryAdapter(Component):
    @property
    def name(self) -> str:
        return "l2_memory"
    
    async def initialize(self) -> None:
        config = get_config()
        self._persist_dir = config.data_dir / "chromadb"
        # 初始化逻辑...
        self._is_available = True
    
    async def shutdown(self) -> None:
        self._is_available = False
```

**初始化**：

```python
components = (L1Buffer(), L2MemoryAdapter(), L3KGAdapter())
manager = ComponentManager(components)
results = await manager.initialize_all()
```

**查询状态**：

```python
status = manager.status

# 检查模块可用性
if status.is_module_available("l2_memory"):
    memory = manager.get_component("l2_memory")

# 获取可用模块列表
available = status.get_available_modules()
```

**卸载**：

```python
async def terminate(self):
    if self.component_manager:
        await self.component_manager.shutdown_all()
```

**模块命名**：

| 模块 | 说明 |
|-----|------|
| `l1_buffer` | L1 内存缓冲 |
| `l2_memory` | L2 记忆库 |
| `l3_kg` | L3 知识图谱 |
| `profile` | 画像存储 |
| `scheduler` | 定时任务 |
| `image_quota` | 图片限额 |

**特性**：故障隔离、异步初始化、动态注册

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
   - 实现位置：`iris_memory/core/components.py`

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