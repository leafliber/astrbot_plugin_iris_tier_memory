# 测试目录结构

本目录按照业务逻辑组织测试文件，与 `iris_memory` 源码结构一一对应。

## 目录结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # Pytest 全局配置和 fixtures
├── README.md                # 本文档
│
├── config/                  # 配置系统测试 (对应 iris_memory/config)
│   ├── __init__.py
│   └── test_config.py       # Config、HiddenConfigManager 测试
│
├── core/                    # 核心工具测试 (对应 iris_memory/core)
│   ├── __init__.py
│   ├── test_logger.py       # 日志模块测试
│   └── test_components.py   # 组件管理器测试
│
└── platform/                # 平台适配器测试 (对应 iris_memory/platform)
    ├── __init__.py
    └── test_platform.py     # PlatformAdapter、OneBot11Adapter 测试
```

## 运行测试

### 运行所有测试

```bash
# 使用 uv
uv run pytest tests/ -v
```

### 运行特定模块测试

```bash
# 配置系统测试
uv run pytest tests/config/ -v

# 核心工具测试
uv run pytest tests/core/ -v

# 平台适配器测试
uv run pytest tests/platform/ -v
```

### 运行特定测试文件

```bash
# 只测试配置系统
uv run pytest tests/config/test_config.py -v

# 只测试组件管理器
uv run pytest tests/core/test_components.py -v
```

## 测试覆盖

### 配置系统 (`config/`)
- ✅ Config 类
  - 扁平化键名访问
  - 配置优先级
  - data_dir 属性
  - 配置变更监听
- ✅ HiddenConfigManager
  - get/set 操作
  - 持久化
  - 默认值

### 核心工具 (`core/`)
- ✅ Logger 模块
  - 日志器获取
  - 名称格式
  - 模块隔离
- ✅ Components 组件管理器
  - SystemStatus 状态管理
  - ComponentManager 生命周期
  - Component 基类
  - 初始化/关闭流程

### 平台适配器 (`platform/`)
- ✅ PlatformAdapter 基类
- ✅ OneBot11Adapter
  - 用户/群组信息获取
  - 群聊判断
- ✅ 工厂方法

## 添加新测试

当添加新的业务模块时，请在 `tests/` 下创建对应的子目录：

```bash
# 示例：添加 models 模块测试
mkdir tests/models
touch tests/models/__init__.py
touch tests/models/test_message.py
```

测试文件命名规范：`test_<模块名>.py`
