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

**测试覆盖**：
- 43 个测试用例，覆盖所有模块
- 测试目录按业务逻辑组织：`tests/config/`、`tests/core/`、`tests/platform/`

**阶段产物**：
```
iris_memory/
├── config/          # 配置系统
├── platform/        # 平台适配器
└── core/            # 核心工具（日志、组件管理器）
main.py              # 插件入口
metadata.yaml        # 插件元数据
_conf_schema.json    # 配置 Schema
requirements.txt     # 依赖清单
```

---

## 阶段 2：L1 消息上下文缓冲

**目标**：消息可按群聊入队，队列满时触发自动总结，总结结果可写入 L2 记忆库（若已初始化）。

**前置依赖**：
- ✅ 阶段1：配置系统、组件管理器、日志系统

**实现步骤**：

1. **实现公共工具** (`iris_memory/utils/token_counter.py`)
   - 使用 `tiktoken` 实现 Token 计数（默认 `cl100k_base` 编码）
   - 封装 `count_tokens(text: str) -> int` 函数
   - 作为公共工具供 L1/L2 使用

2. **创建 L1 缓冲模块** (`iris_memory/l1_buffer/`)
   - `models.py`：定义数据结构
     - `ContextMessage`：消息数据类（role、content、timestamp、token_count、source）
     - `MessageQueue`：队列数据类（group_id、messages、max_length、max_tokens）
   
   - `buffer.py`：L1 缓冲组件
     - 定义 `L1Buffer` 类，继承 `Component`
     - 使用配置系统：`config.get("l1_buffer.max_queue_tokens")`
     - 使用日志系统：`get_logger("l1_buffer")`
     - 实现队列管理：`add_message()`、`get_context()`、`clear_context()`
     - 注册为 `l1_buffer` 模块
   
   - `summarizer.py`：总结器
     - 定义 `Summarizer` 类（依赖 LLM 接口，阶段5实现）
     - 实现总结触发条件判断
     - 使用配置的 `summary_provider`

3. **集成 AstrBot 钩子** (`main.py`)
   - 使用 `@filter.on_llm_request()` 注入队列消息到上下文
   - 使用 `@filter.on_llm_response()` 更新队列
   - 在 `_ensure_initialized()` 中创建 `L1Buffer()` 组件

4. **创建消息处理模块** (`iris_memory/core/message_handler.py`) ✅
   - 实现消息处理器 `handle_user_message()`
   - 使用 `@filter.event_message_type(ALL)` 捕获所有用户消息
   - 将用户消息添加到 L1 Buffer
   - 预留未来处理逻辑扩展点（画像更新、关键词检测等）

5. **重构对话前处理模块** (`iris_memory/core/preprocessor.py`) ✅
   - 专注于 LLM 对话前处理逻辑
   - 实现 L1 上下文注入 `preprocess_llm_request()`
   - 移除消息更新逻辑（已迁移到 message_handler）
   - 预留未来预处理扩展点（画像注入、知识图谱检索等）

6. **调整钩子逻辑** (`main.py`) ✅
   - 新增 `on_all_message()` 钩子：捕获所有用户消息（包括不触发 LLM 的）
   - 调整 `on_llm_response()` 钩子：只添加助手响应，避免重复添加用户消息
   - 确保消息流：用户消息 → on_all_message → L1 Buffer

**完成标志**：
- ✅ 消息可按群聊入队，日志显示入队信息
- ⏳ 队列满时触发总结，日志显示总结结果（待阶段 5 实现）
- ✅ LLM 请求时上下文包含队列消息
- ✅ 所有用户消息（包括不触发 LLM 的）都被添加到 L1 Buffer
- ✅ 消息处理器和对话前处理器分离，架构清晰

**阶段产物**：
```
iris_memory/
├── l1_buffer/              # L1 缓冲模块
│   ├── __init__.py
│   ├── models.py           # 消息数据结构
│   ├── buffer.py           # L1 缓冲组件
│   └── summarizer.py       # 总结器
├── core/                   # 核心模块
│   ├── preprocessor.py     # LLM 对话前处理器 ✅
│   └── message_handler.py  # 消息处理器 ✅
└── utils/                  # 公共工具
    └── token_counter.py    # Token 计数工具
```

**测试要求**：
- `tests/l1_buffer/test_buffer.py`：L1 缓冲组件测试
- `tests/l1_buffer/test_models.py`：数据结构测试
- `tests/l1_buffer/test_summarizer.py`：总结器测试
- `tests/utils/test_token_counter.py`：Token 计数测试
- ✅ `tests/core/test_preprocessor.py`：对话前处理器测试（4 个测试通过）
- ✅ `tests/core/test_message_handler.py`：消息处理器测试（7 个测试通过）

---

## 阶段 3：L2 记忆库

**目标**：可存储记忆向量，支持群聊隔离检索，ChromaDB 不可用时自动降级。

**前置依赖**：
- ✅ 阶段1：配置系统、组件管理器、日志系统
- ✅ 阶段2：L1 缓冲组件

**实现步骤**：

1. **创建 L2 记忆模块** (`iris_memory/l2_memory/`)
   - `models.py`：定义数据结构
     - `MemoryEntry`：记忆数据类（id、content、metadata）
     - `MemorySearchResult`：检索结果（entry、score）
   
   - `adapter.py`：ChromaDB 适配器
     - 定义 `L2MemoryAdapter` 类，继承 `Component`
     - 注册为 `l2_memory` 模块
     - 实现数据库连接、记忆存储、检索、去重
     - 设置超时保护
   
   - `retriever.py`：记忆检索器
     - 定义 `MemoryRetriever` 类
     - 实现 `retrieve()`、`add_from_summary()`
     - 支持图增强检索（依赖 L3）
   
   - `fallback.py`：降级与兜底逻辑
     - 初始化失败时设置不可用
     - 检索时返回空列表

2. **集成到消息钩子** (`main.py`)
   - 在 `_ensure_initialized()` 中创建 `L2MemoryAdapter()` 组件
   - 在 `@filter.on_llm_request()` 中调用检索
   - 在总结完成后写入记忆

**完成标志**：
- 总结后可在 ChromaDB 中查到记忆
- 发送相似问题时，检索结果出现在上下文中
- ChromaDB 连接断开后，主流程不报错

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
```

**测试要求**：
- `tests/l2_memory/test_adapter.py`：适配器测试
- `tests/l2_memory/test_retriever.py`：检索器测试
- `tests/l2_memory/test_models.py`：数据结构测试

---

## 阶段 4：L3 知识图谱

**目标**：可存储知识节点与关系边，支持人格隔离，KuzuDB 不可用时自动降级。

**前置依赖**：
- ✅ 阶段1-3：配置系统、L1 缓冲、L2 记忆库

**实现步骤**：

1. **创建 L3 知识图谱模块** (`iris_memory/l3_kg/`)
   - `models.py`：定义数据结构
     - `GraphNode`：节点数据类（id、type、properties、confidence）
     - `GraphEdge`：边数据类（source_id、target_id、type、weight）
   
   - `adapter.py`：KuzuDB 适配器
     - 定义 `L3KGAdapter` 类，继承 `Component`
     - 注册为 `l3_kg` 模块
     - 实现数据库连接、节点/边管理、查询
     - 设置超时保护
   
   - `retriever.py`：图谱检索器
     - 定义 `GraphRetriever` 类
     - 实现 `retrieve()`、`expand_from_memory()`
     - 支持 L3 检索和图增强检索
   
   - `eviction.py`：容量管理与淘汰
     - 实现 `EvictionManager` 类
     - 检查容量上限、计算遗忘权重
     - 批量淘汰低评分条目

2. **实现遗忘权重算法** (`iris_memory/utils/forgetting.py`)
   - 公共工具，供 L2/L3 使用
   - 计算 R（近因性）、F（频率性）、C（置信度）、D（孤立度）
   - 加权求和得到遗忘评分

3. **集成到消息钩子** (`main.py`)
   - 在 `_ensure_initialized()` 中创建 `L3KGAdapter()` 组件
   - 在 `@filter.on_llm_request()` 中调用图谱检索

**完成标志**：
- 总结后可在 KuzuDB 中查到节点和边
- 发送相关问题时，图谱关系被检索
- KuzuDB 不可用时，日志显示降级

**阶段产物**：
```
iris_memory/
├── l3_kg/                  # L3 知识图谱模块
│   ├── __init__.py
│   ├── models.py           # 图谱数据结构
│   ├── adapter.py          # KuzuDB 适配器
│   ├── retriever.py        # 图谱检索器
│   └── eviction.py         # 容量管理
└── utils/                  # 公共工具（新增）
    └── forgetting.py       # 遗忘权重算法
```

**测试要求**：
- `tests/l3_kg/test_adapter.py`：适配器测试
- `tests/l3_kg/test_retriever.py`：检索器测试
- `tests/utils/test_forgetting.py`：遗忘算法测试

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