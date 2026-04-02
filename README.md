# Iris Tier Memory

AstrBot 分层记忆系统插件

## 简介

Iris Tier Memory 是一个为 AstrBot 设计的分层记忆系统插件，提供三阶段记忆管理和用户画像功能。

## 功能特性

- **L1 消息缓冲**：短期上下文记忆，自动总结
- **L2 记忆库**：中期记忆存储（ChromaDB 向量检索）
- **L3 知识图谱**：长期结构化知识（KuzuDB 图数据库）
- **用户画像**：自动构建和维护用户/群聊画像
- **Web 管理界面**：可视化管理记忆和画像

## 安装

将此插件放入 AstrBot 的 `data/plugins` 目录下，或在 AstrBot 插件市场搜索安装。

## 配置管理员

使用 `iris_mem` 指令需要管理员权限：

1. 使用 `/sid` 指令获取你的用户 ID
2. 在 AstrBot WebUI → 配置 → 其他配置 → 管理员 ID 列表中添加你的 ID

## 指令使用

### 基本格式

```
/iris_mem <模块> <子指令> [参数]
```

### 模块说明

| 模块 | 说明 |
|------|------|
| `l1` | L1 消息缓冲管理 |
| `l2` | L2 记忆库管理 |
| `l3` | L3 知识图谱管理 |
| `profile` | 画像管理 |
| `all` | 总删除开关（同时操作所有层级） |

### L1 消息缓冲

```bash
# 查看统计
/iris_mem l1 stats

# 清空当前用户的 L1
/iris_mem l1 clear

# 清空指定用户的 L1（@用户）
/iris_mem l1 clear @张三

# 清空当前群聊的 L1
/iris_mem l1 clear --group

# 清空所有 L1
/iris_mem l1 clear --all
```

### L2 记忆库

```bash
# 查看统计
/iris_mem l2 stats

# 清空当前用户的 L2 记忆
/iris_mem l2 clear

# 清空指定用户的 L2 记忆
/iris_mem l2 clear @用户

# 清空当前群聊的 L2 记忆
/iris_mem l2 clear --group

# 清空所有 L2 记忆
/iris_mem l2 clear --all
```

### L3 知识图谱

```bash
# 查看统计
/iris_mem l3 stats

# 清空当前用户的 L3 知识图谱
/iris_mem l3 clear

# 清空指定用户的 L3 知识图谱
/iris_mem l3 clear @用户

# 清空当前群聊的 L3 知识图谱
/iris_mem l3 clear --group

# 清空所有 L3 知识图谱
/iris_mem l3 clear --all
```

### 画像管理

```bash
# 显示当前用户画像
/iris_mem profile show

# 显示指定用户画像
/iris_mem profile show @用户

# 重置当前用户画像
/iris_mem profile reset

# 重置指定用户画像
/iris_mem profile reset @用户

# 重置当前群聊所有用户画像
/iris_mem profile reset --group

# 重置所有用户画像
/iris_mem profile reset --all

# 群聊画像操作
/iris_mem profile group show      # 显示群聊画像
/iris_mem profile group reset     # 重置群聊画像
```

### 总删除（含画像）

```bash
# 清空当前用户所有记忆和画像
/iris_mem all clear

# 清空指定用户所有记忆和画像
/iris_mem all clear @用户

# 清空当前群聊所有记忆和画像
/iris_mem all clear --group

# 清空所有记忆和画像
/iris_mem all clear --all
```

### 帮助

```bash
# 显示帮助
/iris_mem help

# 显示模块帮助
/iris_mem l1 help
/iris_mem profile help
```

## 删除粒度说明

| 粒度 | 说明 |
|------|------|
| 默认（无参数） | 仅操作当前用户在当前群聊的数据 |
| `@用户` | 操作指定用户在当前群聊的数据 |
| `--group` / `-g` | 操作当前群聊的所有数据 |
| `--all` / `-a` | 操作所有数据（全局） |

## 项目结构

```
astrbot_plugin_iris_tier_memory/
├── main.py                    # 插件入口
├── iris_memory/
│   ├── commands/              # 指令模块
│   │   ├── executor.py        # 指令执行器
│   │   ├── parser.py          # 指令解析
│   │   ├── registry.py        # 指令注册
│   │   ├── l1_handler.py      # L1 处理器
│   │   ├── l2_handler.py      # L2 处理器
│   │   ├── l3_handler.py      # L3 处理器
│   │   ├── profile_handler.py # 画像处理器
│   │   └── all_handler.py     # 总删除处理器
│   ├── l1_buffer/             # L1 消息缓冲
│   ├── l2_memory/             # L2 记忆库
│   ├── l3_kg/                 # L3 知识图谱
│   ├── profile/               # 用户画像
│   ├── tools/                 # LLM 工具
│   └── web/                   # Web 管理界面
└── tests/                     # 测试代码
```

## 相关资源

- [AstrBot 主项目](https://github.com/AstrBotDevs/AstrBot)
- [插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)

## 许可证

AGPL-3.0
