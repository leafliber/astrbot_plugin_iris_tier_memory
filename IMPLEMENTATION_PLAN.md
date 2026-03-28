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

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib

# 节点类型白名单
NODE_TYPE_WHITELIST = {"Person", "Event", "Concept", "Location", "Item", "Topic"}

# 关系类型白名单
RELATION_TYPE_WHITELIST = {
    "KNOWS", "MENTIONED_IN", "RELATED_TO", 
    "PART_OF", "LOCATED_AT", "HAPPENED_AT"
}

@dataclass
class GraphNode:
    """图谱节点"""
    id: str                                    # 节点唯一ID（基于内容hash）
    label: str                                 # 节点类型标签（动态）
    name: str                                  # 实体名称
    content: str                               # 完整描述内容
    confidence: float = 1.0                    # 置信度 [0.3, 1.0]
    access_count: int = 0                      # 访问次数
    last_access_time: Optional[datetime] = None
    created_time: datetime = field(default_factory=datetime.now)
    source_memory_id: Optional[str] = None     # 来源记忆ID
    group_id: Optional[str] = None             # 群聊ID（用于隔离）
    properties: dict = field(default_factory=dict)  # 扩展属性
    
    def generate_id(self) -> str:
        """基于内容生成唯一ID"""
        content_hash = hashlib.md5(
            f"{self.label}:{self.name}:{self.content}".encode()
        ).hexdigest()
        return f"{self.label.lower()}_{content_hash[:12]}"

@dataclass
class GraphEdge:
    """图谱边"""
    source_id: str                             # 源节点ID
    target_id: str                             # 目标节点ID
    relation_type: str                         # 关系类型（动态）
    weight: float = 1.0                        # 边权重 [0.0, 1.0]
    confidence: float = 1.0                    # 置信度
    access_count: int = 0                      # 访问次数
    last_access_time: Optional[datetime] = None
    created_time: datetime = field(default_factory=datetime.now)
    source_memory_id: Optional[str] = None     # 来源记忆ID
    properties: dict = field(default_factory=dict)
    
    def generate_id(self) -> str:
        """生成边唯一标识"""
        return f"{self.source_id}_{self.relation_type}_{self.target_id}"

@dataclass
class ExtractionResult:
    """实体提取结果"""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    extraction_confidence: float = 1.0         # 提取置信度
```

### ✅ 4.2 实现 KuzuDB 适配器 (`iris_memory/l3_kg/adapter.py`)

```python
from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
import kuzu
from pathlib import Path
from typing import Optional

logger = get_logger("l3_kg")

class L3KGAdapter(Component):
    """KuzuDB 图谱适配器"""
    
    @property
    def name(self) -> str:
        return "l3_kg"
    
    async def initialize(self) -> None:
        config = get_config()
        
        # 检查是否启用
        if not config.get("l3_kg.enable"):
            logger.info("L3 知识图谱未启用")
            self._is_available = False
            return
        
        # 初始化 KuzuDB
        self._persist_dir = config.data_dir / "kuzu"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 创建数据库连接
            self._db = kuzu.Database(str(self._persist_dir))
            self._conn = kuzu.Connection(self._db)
            
            # 创建 schema
            await self._create_schema()
            
            self._is_available = True
            logger.info(f"KuzuDB 初始化成功：{self._persist_dir}")
        except Exception as e:
            logger.error(f"KuzuDB 初始化失败：{e}")
            self._is_available = False
    
    async def _create_schema(self):
        """创建图谱 schema"""
        # 创建节点表（动态类型通过 label 字段实现）
        self._conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS Entity (
                id STRING PRIMARY KEY,
                label STRING,
                name STRING,
                content STRING,
                confidence DOUBLE,                   -- ✅ 使用 DOUBLE（精度更高）
                access_count INT64,
                last_access_time TIMESTAMP,
                created_time TIMESTAMP,
                source_memory_id STRING,
                group_id STRING,
                properties MAP<STRING, STRING>       -- ✅ 使用 MAP 类型（类型安全）
            )
        """)
        
        # 创建关系表（动态类型通过 relation_type 字段实现）
        self._conn.execute("""
            CREATE REL TABLE IF NOT EXISTS Related (
                FROM Entity TO Entity,
                relation_type STRING,
                weight DOUBLE,                        -- ✅ 使用 DOUBLE（精度更高）
                confidence DOUBLE,                    -- ✅ 使用 DOUBLE（精度更高）
                access_count INT64,
                last_access_time TIMESTAMP,
                created_time TIMESTAMP,
                source_memory_id STRING,
                properties MAP<STRING, STRING>        -- ✅ 使用 MAP 类型（类型安全）
            )
        """)
        
        logger.debug("KuzuDB schema 创建完成")
    
    async def add_node(self, node: GraphNode) -> bool:
        """添加节点"""
        if not self._is_available:
            return False
        
        try:
            query = """
                MERGE (e:Entity {id: $id})
                SET e.label = $label,
                    e.name = $name,
                    e.content = $content,
                    e.confidence = $confidence,
                    e.access_count = $access_count,
                    e.last_access_time = $last_access_time,
                    e.created_time = $created_time,
                    e.source_memory_id = $source_memory_id,
                    e.group_id = $group_id,
                    e.properties = $properties
            """
            self._conn.execute(query, {
                "id": node.id,
                "label": node.label,
                "name": node.name,
                "content": node.content,
                "confidence": node.confidence,
                "access_count": node.access_count,
                "last_access_time": node.last_access_time or datetime.now(),
                "created_time": node.created_time,
                "source_memory_id": node.source_memory_id,
                "group_id": node.group_id,
                "properties": json.dumps(node.properties)
            })
            return True
        except Exception as e:
            logger.error(f"添加节点失败：{e}")
            return False
    
    async def add_edge(self, edge: GraphEdge) -> bool:
        """添加关系边"""
        if not self._is_available:
            return False
        
        try:
            query = """
                MATCH (src:Entity {id: $source_id})
                MATCH (tgt:Entity {id: $target_id})
                MERGE (src)-[r:Related {relation_type: $relation_type}]->(tgt)
                SET r.weight = $weight,
                    r.confidence = $confidence,
                    r.access_count = $access_count,
                    r.last_access_time = $last_access_time,
                    r.created_time = $created_time,
                    r.source_memory_id = $source_memory_id,
                    r.properties = $properties
            """
            self._conn.execute(query, {
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation_type": edge.relation_type,
                "weight": edge.weight,
                "confidence": edge.confidence,
                "access_count": edge.access_count,
                "last_access_time": edge.last_access_time or datetime.now(),
                "created_time": edge.created_time,
                "source_memory_id": edge.source_memory_id,
                "properties": json.dumps(edge.properties)
            })
            return True
        except Exception as e:
            logger.error(f"添加边失败：{e}")
            return False
    
    async def expand_from_nodes(
        self, 
        node_ids: list[str], 
        max_depth: int = 2,
        group_id: Optional[str] = None
    ) -> tuple[list[dict], list[dict]]:
        """路径扩展检索
        
        从指定节点出发，查找相关路径
        返回：(节点列表, 边列表)
        """
        if not self._is_available:
            return [], []
        
        try:
            # 构建路径查询
            query = """
                MATCH path = (start:Entity)-[r:Related*1..%d]-(end:Entity)
                WHERE start.id IN $node_ids
                AND ($group_id IS NULL OR start.group_id = $group_id)
                RETURN 
                    nodes(path) as nodes,
                    relationships(path) as edges
            """ % max_depth
            
            result = self._conn.execute(query, {
                "node_ids": node_ids,
                "group_id": group_id
            })
            
            nodes = []
            edges = []
            for row in result:
                nodes.extend(row["nodes"])
                edges.extend(row["edges"])
            
            # 去重
            nodes = list({n["id"]: n for n in nodes}.values())
            edges = list({f"{e['source']}-{e['relation_type']}-{e['target']}": e for e in edges}.values())
            
            return nodes, edges
        except Exception as e:
            logger.error(f"路径扩展检索失败：{e}")
            return [], []
    
    async def get_stats(self) -> dict:
        """获取图谱统计信息"""
        if not self._is_available:
            return {"available": False}
        
        try:
            node_count = self._conn.execute("MATCH (e:Entity) RETURN COUNT(e) as count").get_next()[0]
            edge_count = self._conn.execute("MATCH ()-[r:Related]->() RETURN COUNT(r) as count").get_next()[0]
            
            return {
                "available": True,
                "node_count": node_count,
                "edge_count": edge_count,
                "persist_dir": str(self._persist_dir)
            }
        except Exception as e:
            logger.error(f"获取图谱统计失败：{e}")
            return {"available": False}
    
    async def shutdown(self) -> None:
        if self._conn:
            self._conn.close()
        if self._db:
            self._db.close()
        self._is_available = False
        logger.info("KuzuDB 已关闭")
```

### ✅ 4.3 实现实体提取器 (`iris_memory/l3_kg/extractor.py`)

```python
from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import GraphNode, GraphEdge, ExtractionResult, NODE_TYPE_WHITELIST, RELATION_TYPE_WHITELIST
import json

logger = get_logger("l3_kg")

class EntityExtractor:
    """实体和关系提取器"""
    
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.config = get_config()
    
    async def extract_from_text(
        self, 
        text: str, 
        context: dict = None
    ) -> ExtractionResult:
        """从文本中提取实体和关系
        
        Args:
            text: 待提取的文本（总结内容）
            context: 上下文信息（group_id, source_memory_id等）
        
        Returns:
            ExtractionResult: 提取结果
        """
        # 构建提取 prompt
        prompt = self._build_extraction_prompt(text)
        
        try:
            # 调用 LLM 提取
            response = await self.llm_manager.generate(
                prompt=prompt,
                temperature=0.3,  # 低温度保证稳定性
                module="l3_kg_extraction"
            )
            
            # 解析提取结果
            result = self._parse_extraction_result(response, context)
            
            logger.info(
                f"实体提取完成：{len(result.nodes)} 个节点，"
                f"{len(result.edges)} 条边"
            )
            
            return result
        except Exception as e:
            logger.error(f"实体提取失败：{e}")
            return ExtractionResult()
    
    def _build_extraction_prompt(self, text: str) -> str:
        """构建提取 prompt"""
        return f"""从以下文本中提取实体和关系。

## 节点类型白名单（优先使用）
{', '.join(NODE_TYPE_WHITELIST)}

## 关系类型白名单（优先使用）
{', '.join(RELATION_TYPE_WHITELIST)}

## 提取规则
1. 识别文本中的关键实体（人物、事件、概念、地点、物品、话题）
2. 识别实体之间的关系
3. 如果实体类型不在白名单中，可以创建新类型，但要保持命名规范
4. 如果关系类型不在白名单中，可以创建新类型
5. 评估提取置信度（0.3-1.0）

## 输出格式（JSON）
{{
  "nodes": [
    {{
      "label": "Person",
      "name": "实体名称",
      "content": "实体描述",
      "confidence": 0.9
    }}
  ],
  "edges": [
    {{
      "source_name": "源实体名称",
      "target_name": "目标实体名称",
      "relation_type": "KNOWS",
      "confidence": 0.8
    }}
  ],
  "extraction_confidence": 0.85
}}

## 待提取文本
{text}

## 输出
请严格按照 JSON 格式输出，不要添加任何其他内容。"""

    def _parse_extraction_result(
        self, 
        response: str, 
        context: dict
    ) -> ExtractionResult:
        """解析 LLM 提取结果"""
        try:
            # 清理响应（去除 markdown 代码块标记）
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            data = json.loads(response.strip())
            
            # 构建节点
            nodes = []
            node_name_to_id = {}
            
            for node_data in data.get("nodes", []):
                node = GraphNode(
                    id="",  # 稍后生成
                    label=node_data["label"],
                    name=node_data["name"],
                    content=node_data["content"],
                    confidence=node_data.get("confidence", 1.0),
                    source_memory_id=context.get("source_memory_id"),
                    group_id=context.get("group_id")
                )
                node.id = node.generate_id()
                nodes.append(node)
                node_name_to_id[node.name] = node.id
            
            # 构建边
            edges = []
            for edge_data in data.get("edges", []):
                source_id = node_name_to_id.get(edge_data["source_name"])
                target_id = node_name_to_id.get(edge_data["target_name"])
                
                if source_id and target_id:
                    edge = GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relation_type=edge_data["relation_type"],
                        confidence=edge_data.get("confidence", 1.0),
                        source_memory_id=context.get("source_memory_id")
                    )
                    edges.append(edge)
            
            return ExtractionResult(
                nodes=nodes,
                edges=edges,
                extraction_confidence=data.get("extraction_confidence", 1.0)
            )
        except Exception as e:
            logger.error(f"解析提取结果失败：{e}")
            return ExtractionResult()
```

### ✅ 4.4 实现图谱检索器 (`iris_memory/l3_kg/retriever.py`)

```python
from iris_memory.core import get_logger
from iris_memory.config import get_config
from .adapter import L3KGAdapter
from .models import GraphNode, GraphEdge
import asyncio

logger = get_logger("l3_kg")

class GraphRetriever:
    """图谱检索器"""
    
    def __init__(self, adapter: L3KGAdapter):
        self.adapter = adapter
        self.config = get_config()
    
    async def retrieve_with_expansion(
        self,
        memory_node_ids: list[str],
        group_id: str = None
    ) -> tuple[list[dict], list[dict]]:
        """图增强检索：基于向量检索命中的记忆节点进行路径扩展
        
        Args:
            memory_node_ids: 向量检索命中的记忆对应的节点ID列表
            group_id: 群聊ID
        
        Returns:
            (节点列表, 边列表)
        """
        if not self.adapter._is_available:
            return [], []
        
        try:
            # 获取扩展深度配置
            max_depth = self.config.get("l3_kg.expansion_depth", 2)
            timeout_ms = self.config.get("l3_kg.timeout_ms", 1500)
            
            # 设置超时保护
            nodes, edges = await asyncio.wait_for(
                self.adapter.expand_from_nodes(
                    node_ids=memory_node_ids,
                    max_depth=max_depth,
                    group_id=group_id
                ),
                timeout=timeout_ms / 1000
            )
            
            logger.info(
                f"图增强检索完成：{len(nodes)} 个节点，"
                f"{len(edges)} 条边，深度 {max_depth}"
            )
            
            return nodes, edges
        except asyncio.TimeoutError:
            logger.warning(f"图增强检索超时（{timeout_ms}ms），跳过")
            return [], []
        except Exception as e:
            logger.error(f"图增强检索失败：{e}")
            return [], []
    
    async def update_access_count(self, node_ids: list[str]):
        """更新节点访问计数"""
        if not self.adapter._is_available:
            return
        
        try:
            # 批量更新节点访问计数
            for node_id in node_ids:
                self.adapter._conn.execute("""
                    MATCH (e:Entity {id: $id})
                    SET e.access_count = e.access_count + 1,
                        e.last_access_time = $now
                """, {"id": node_id, "now": datetime.now()})
        except Exception as e:
            logger.error(f"更新节点访问计数失败：{e}")
    
    def format_for_context(
        self,
        nodes: list[dict],
        edges: list[dict]
    ) -> str:
        """格式化图谱结果为上下文文本
        
        Args:
            nodes: 节点列表
            edges: 边列表
        
        Returns:
            格式化的文本
        """
        if not nodes:
            return ""
        
        lines = ["## 知识图谱关联信息"]
        
        # 按类型分组节点
        nodes_by_type = {}
        for node in nodes:
            label = node.get("label", "Unknown")
            if label not in nodes_by_type:
                nodes_by_type[label] = []
            nodes_by_type[label].append(node)
        
        # 输出节点
        for label, type_nodes in nodes_by_type.items():
            lines.append(f"\n### {label}")
            for node in type_nodes:
                lines.append(f"- {node['name']}: {node['content']}")
        
        # 输出关系
        if edges:
            lines.append("\n### 关系")
            for edge in edges:
                lines.append(
                    f"- {edge['source_name']} --[{edge['relation_type']}]--> "
                    f"{edge['target_name']}"
                )
        
        return "\n".join(lines)
```

### ⏳ 4.5 集成实体提取到总结流程

**L1 缓冲总结后提取** (`iris_memory/l1_buffer/summarizer.py` 修改):

```python
async def summarize(self, messages: list[dict], group_id: str):
    """总结消息队列"""
    # 原有总结逻辑...
    summary_text = await self.llm_manager.generate(...)
    
    # 新增：提取实体和关系
    if self.config.get("l3_kg.enable"):
        try:
            extractor = EntityExtractor(self.llm_manager)
            extraction_result = await extractor.extract_from_text(
                text=summary_text,
                context={
                    "group_id": group_id,
                    "source_memory_id": memory_id
                }
            )
            
            # 存储到图谱
            kg_adapter = self.component_manager.get_component("l3_kg")
            for node in extraction_result.nodes:
                await kg_adapter.add_node(node)
            for edge in extraction_result.edges:
                await kg_adapter.add_edge(edge)
        except Exception as e:
            logger.warning(f"L1 总结后实体提取失败（不影响主流程）：{e}")
```

**L2 记忆总结后提取** (`iris_memory/l2_memory/retriever.py` 修改):

```python
async def summarize_memories(self, memories: list[dict], group_id: str):
    """合并相似记忆"""
    # 原有合并逻辑...
    merged_text = await self.llm_manager.generate(...)
    
    # 新增：提取实体和关系（类似 L1）
    if self.config.get("l3_kg.enable"):
        # ... 同 L1 的提取逻辑
```

### ✅ 4.6 实现 LLM Tool：保存知识 (`iris_memory/tools/save_knowledge.py`)

```python
from astrbot.api import filter
from iris_memory.core import get_logger
from iris_memory.l3_kg import GraphNode, GraphEdge

logger = get_logger("tools")

@filter.llm_tool(name="save_knowledge")
async def save_knowledge(
    nodes: list[dict],
    edges: list[dict]
) -> str:
    """保存知识到图谱
    
    Args:
        nodes: 节点列表，每个节点包含 label, name, content, confidence
        edges: 边列表，每个边包含 source_name, target_name, relation_type, confidence
    
    Returns:
        操作结果描述
    """
    try:
        kg_adapter = get_component("l3_kg")
        if not kg_adapter._is_available:
            return "知识图谱不可用"
        
        # 构建 GraphNode 对象
        graph_nodes = []
        for node_data in nodes:
            node = GraphNode(
                id="",
                label=node_data["label"],
                name=node_data["name"],
                content=node_data["content"],
                confidence=node_data.get("confidence", 1.0)
            )
            node.id = node.generate_id()
            graph_nodes.append(node)
        
        # 构建 GraphEdge 对象
        node_name_to_id = {n.name: n.id for n in graph_nodes}
        graph_edges = []
        for edge_data in edges:
            source_id = node_name_to_id.get(edge_data["source_name"])
            target_id = node_name_to_id.get(edge_data["target_name"])
            
            if source_id and target_id:
                edge = GraphEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=edge_data["relation_type"],
                    confidence=edge_data.get("confidence", 1.0)
                )
                graph_edges.append(edge)
        
        # 存储到图谱
        added_nodes = 0
        added_edges = 0
        for node in graph_nodes:
            if await kg_adapter.add_node(node):
                added_nodes += 1
        
        for edge in graph_edges:
            if await kg_adapter.add_edge(edge):
                added_edges += 1
        
        return f"成功保存 {added_nodes} 个节点和 {added_edges} 条边"
    except Exception as e:
        logger.error(f"保存知识失败：{e}")
        return f"保存失败：{str(e)}"
```

### ⏳ 4.7 集成到主程序 (`main.py`)

```python
async def _ensure_initialized(self):
    """初始化组件"""
    if self._initialized:
        return
    
    # 创建组件
    components = [
        L1Buffer(),
        L2MemoryAdapter(),
        L3KGAdapter(),  # 新增
    ]
    
    self.component_manager = ComponentManager(components)
    await self.component_manager.initialize_all()
    
    self._initialized = True

@filter.on_llm_request()
async def on_llm_request(event: AstrBotMessageEvent):
    """LLM 请求钩子：注入图谱检索结果"""
    # ... L1/L2 检索逻辑
    
    # 新增：图增强检索
    if config.get("l3_kg.enable") and config.get("l2_memory.enable_graph_enhancement"):
        kg_adapter = component_manager.get_component("l3_kg")
        retriever = GraphRetriever(kg_adapter)
        
        # 从 L2 检索结果中提取节点ID
        memory_node_ids = [m.get("node_id") for m in l2_results if m.get("node_id")]
        
        if memory_node_ids:
            graph_nodes, graph_edges = await retriever.retrieve_with_expansion(
                memory_node_ids,
                group_id=group_id
            )
            
            # 格式化并注入上下文
            graph_context = retriever.format_for_context(graph_nodes, graph_edges)
            if graph_context:
                context_parts.append(graph_context)
```

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
```json
{
  "l3_kg": {
    "enable": {
      "type": "boolean",
      "default": true,
      "description": "启用 L3 知识图谱"
    },
    "max_nodes": {
      "type": "integer",
      "default": 50000,
      "description": "最大节点数"
    },
    "max_edges": {
      "type": "integer",
      "default": 100000,
      "description": "最大边数"
    },
    "timeout_ms": {
      "type": "integer",
      "default": 1500,
      "description": "查询超时时间（毫秒）"
    },
    "expansion_depth": {
      "type": "integer",
      "default": 2,
      "description": "图增强检索的路径扩展深度"
    },
    "enable_type_whitelist": {
      "type": "boolean",
      "default": true,
      "description": "启用类型白名单约束"
    }
  }
}
```

**隐藏配置**（`hidden_config.json`）：
```json
{
  "kuzu_query_timeout_ms": 1500,
  "entity_extraction_temperature": 0.3,
  "type_merge_threshold": 0.8,
  "type_similarity_model": "text-embedding-3-small",
  "node_confidence_threshold": 0.3,
  "edge_weight_decay_rate": 0.01,
  "forgetting_lambda_kg": 0.01,
  "forgetting_threshold_kg": 0.2,
  "kg_retention_days": 30
}
```

**测试要求**：
- `tests/l3_kg/test_models.py`：数据结构测试
- `tests/l3_kg/test_adapter.py`：适配器测试（初始化、节点/边操作、查询、降级）
- `tests/l3_kg/test_extractor.py`：提取器测试（prompt 构建、结果解析）
- `tests/l3_kg/test_retriever.py`：检索器测试（路径扩展、超时保护、格式化）
- `tests/l3_kg/test_eviction.py`：淘汰机制测试
- `tests/tools/test_save_knowledge.py`：Tool 测试

---

## 阶段 5：LLM 调用统一管理

**目标**：提供统一的 LLM 调用入口，支持 Token 统计与调用模块追踪。

**前置依赖**：
- ✅ 阶段1-4：配置系统、L1-L3 模块

**实现步骤**：

1. **创建 LLM 管理模块** (`iris_memory/llm/`)
   - `manager.py`：LLM 调用管理器
     - 定义 `LLMManager` 类
     - 实现 `generate()`、`generate_with_tools()`
     - 记录 Token 使用量和调用模块
   
   - `token_stats.py`：Token 统计
     - 定义 `TokenStats`、`TokenStatsManager` 类
     - 记录、查询、重置统计
   
   - `call_log.py`：调用记录
     - 定义 `CallLog` 数据类
     - 使用 `deque` 存储最近 N 条记录

2. **集成到各模块**
   - L1 Summarizer 使用 `LLMManager.generate()`
   - L2 MemoryRetriever 使用 `LLMManager.generate()`
   - 统一调用路径

**完成标志**：
- 总结与检索时，日志显示 Token 使用量
- 调用统计可通过接口查询

**阶段产物**：
```
iris_memory/
└── llm/                    # LLM 管理模块
    ├── __init__.py
    ├── manager.py          # LLM 调用管理器
    ├── token_stats.py      # Token 统计
    └── call_log.py         # 调用记录
```

**测试要求**：
- `tests/llm/test_manager.py`：管理器测试
- `tests/llm/test_token_stats.py`：统计测试

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