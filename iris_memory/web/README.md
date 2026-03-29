# Iris Memory Web 模块

## 📋 概述

为 Iris Tier Memory 插件提供现代化的 Web 可视化界面，支持记忆管理、画像编辑和统计图表展示。

## 🏗️ 架构

- **后端**：Quart (异步 Flask-like 框架)
- **前端**：Vue.js 3 + Vuetify 3 + TypeScript
- **认证**：复用 AstrBot Dashboard JWT
- **端口**：独立端口 9967（可配置）

## 🚀 快速开始

### 后端部署

后端已集成到插件中，插件加载时自动启动独立 HTTP 服务器：

**配置方式**（在 AstrBot 管理界面配置）：
- `web.enable`: 是否启用 Web 服务器（默认 `true`）
- `web.host`: 监听地址（默认 `0.0.0.0`）
- `web.port`: 独立端口（默认 `9967`）

**启动后访问**：
- API: `http://localhost:9967/api/iris/memory/l2/search`
- 前端: `http://localhost:9967/iris`

**端口说明**：
- Web 服务器使用独立端口（默认 9967），与 AstrBot 主端口（6185）分离
- 独立端口设计避免了 AstrBot StarContext 无法暴露 Quart app 实例的问题
- 支持多插件并行，不会产生端口冲突

### 前端开发

#### 1. 安装依赖

```bash
cd iris_memory/web/frontend
npm install
```

#### 2. 开发模式

```bash
npm run dev
```

访问 `http://localhost:5173`

#### 3. 构建生产版本

```bash
npm run build
```

构建产物会输出到 `dist/` 目录，由 Quart 自动托管。

#### 4. 访问 Web 界面

构建完成后，访问：`http://localhost:9967/iris`（或配置的端口）

## 📁 项目结构

```
iris_memory/web/
├── __init__.py              # Web模块入口，注册路由
├── auth.py                  # JWT认证中间件
├── routes/                  # API路由
│   ├── memory.py           # 记忆API（L1/L2/L3）
│   ├── profile.py          # 画像API
│   └── stats.py            # 统计API
└── frontend/                # 前端项目
    ├── src/
    │   ├── api/             # API封装
    │   ├── views/           # 页面组件
    │   ├── stores/          # Pinia状态管理
    │   ├── router/          # Vue Router配置
    │   ├── App.vue          # 根组件
    │   └── main.ts          # 入口文件
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
```

## 🔐 认证机制

### JWT 认证

- **安全策略**：完整JWT签名验证（防止Token伪造）
- **密钥来源**：AstrBot 配置文件 `data/cmd_config.json`
- **适用版本**：AstrBot > 3.5.17（已修复CVE-2025-55449）

### 认证流程

1. 用户登录 AstrBot Dashboard (`http://localhost:6185`)
2. JWT Token 存储在 Cookie 中
3. 前端访问 Iris Memory API (`http://localhost:9967/api/iris/*`)
4. 浏览器自动携带 Cookie
5. 后端验证 JWT 签名和用户身份

**注意**：由于独立端口部署，需要确保浏览器支持跨端口 Cookie 携带（SameSite=None）。

### 访问控制

所有 API 都需要认证：

```python
@memory_bp.route('/l2/search', methods=['POST'])
@dashboard_auth.require_auth
async def search_l2_memory():
    # 已认证，可访问
    pass
```

## 📊 API 文档

### Memory API

#### POST /api/iris/memory/l2/search

搜索 L2 记忆库

**请求体**：
```json
{
  "query": "搜索关键词",
  "group_id": "群聊ID（可选）",
  "top_k": 10
}
```

**响应**：
```json
{
  "success": true,
  "results": [
    {
      "content": "记忆内容",
      "score": 0.95,
      "metadata": {},
      "timestamp": "2026-03-29T12:00:00"
    }
  ]
}
```

#### GET /api/iris/memory/l1/list

获取 L1 缓冲列表

**查询参数**：
- `group_id`: 群聊ID（可选）

#### GET /api/iris/memory/l3/graph

获取 L3 知识图谱数据

### Profile API

#### GET /api/iris/profile/group/:id

获取群聊画像

#### PUT /api/iris/profile/group/:id

更新群聊画像

#### GET /api/iris/profile/user/:id

获取用户画像

### Stats API

#### GET /api/iris/stats/token

获取 Token 使用统计

#### GET /api/iris/stats/memory

获取记忆统计

#### GET /api/iris/stats/kg

获取知识图谱统计

## 🧪 测试

### 后端测试

```bash
# 运行后端API测试
pytest tests/web/
```

### 前端测试

```bash
cd frontend
npm run test
```

## 🔧 故障排查

### 端口冲突

如果 9967 端口被占用：
1. 修改配置：在 AstrBot 管理界面将 `web.port` 改为其他端口
2. 或暂时禁用 Web 服务器：`web.enable = false`

### 跨域 Cookie 问题

如果浏览器不携带 Cookie：
1. 确认 AstrBot 版本 > 3.5.17
2. 检查浏览器设置：允许第三方 Cookie
3. 或使用相同端口部署（需要 AstrBot 支持）

### 前端构建失败

确保已安装 Node.js 18+ 和 npm：

```bash
node --version
npm --version
```

### JWT 认证失败

1. 确认 AstrBot 版本 > 3.5.17
2. 检查 `data/cmd_config.json` 中是否存在 `jwt_secret`
3. 重新登录 AstrBot Dashboard (`http://localhost:6185`)
4. 清除浏览器 Cookie 后重新登录

### API 503 错误

组件未初始化或不可用：

1. 检查组件状态：访问 `/api/iris/stats/system`
2. 查看日志：确认组件是否正常启动
3. 检查配置：确认相关功能已启用

## 📝 开发指南

### 添加新 API

1. 在 `routes/` 目录创建新路由文件
2. 使用 `@dashboard_auth.require_auth` 装饰器保护路由
3. 在 `routes/__init__.py` 中导出 Blueprint
4. 在 `web/__init__.py` 中注册路由

### 添加前端页面

1. 在 `frontend/src/views/` 创建 Vue 组件
2. 在 `frontend/src/router/index.ts` 添加路由配置
3. 在 `frontend/src/api/` 创建对应的 API 封装
4. 在 `frontend/src/stores/` 创建 Pinia Store

## 📄 许可证

MIT License
