"""
Web 模块 - 提供前后端分离的 Web 界面

架构：
- 后端：Quart API（独立端口）
- 前端：Vue.js 3 SPA（构建后由 Quart 托管）
- 认证：复用 AstrBot Dashboard JWT

使用方式：
    # 方式1：独立 HTTP 服务器（推荐）
    from iris_memory.web import create_app, WebServer
    
    server = WebServer(port=9967)
    server.start()
    
    # 方式2：注册到现有应用（需要 app 实例）
    from iris_memory.web import register_routes
    register_routes(context.app)
"""
from quart import Blueprint, send_from_directory, Quart, request, Response
from pathlib import Path
from typing import Any, Optional

from .routes.memory import memory_bp
from .routes.profile import profile_bp
from .routes.stats import stats_bp
from .auth import dashboard_auth
from .server import WebServer, create_web_server_from_config
from iris_memory.core import get_logger

logger = get_logger("web")

__all__ = ['create_app', 'register_routes', 'dashboard_auth', 'WebServer', 'create_web_server_from_config']


def _add_cors_headers(response: Response, origins: str) -> Response:
    """添加 CORS 响应头
    
    Args:
        response: Quart 响应对象
        origins: 允许的源（逗号分隔）
        
    Returns:
        添加了 CORS 头的响应对象
    """
    # 处理多源配置
    origin_list = [o.strip() for o in origins.split(',')]
    request_origin = request.headers.get('Origin', '')
    
    # 判断是否允许该源
    if origins == '*' or request_origin in origin_list:
        response.headers['Access-Control-Allow-Origin'] = request_origin if request_origin else '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    
    return response


def create_app(cors_origins: str = "*") -> Quart:
    """
    创建独立的 Quart 应用实例
    
    Args:
        cors_origins: CORS 允许的源（逗号分隔）
    
    Returns:
        Quart 应用实例，已注册所有路由
    
    使用场景：
        用于独立 HTTP 服务器，不依赖 AstrBot 主应用。
    
    Example:
        >>> from iris_memory.web import create_app, WebServer
        >>> app = create_app()
        >>> server = WebServer(port=9967)
        >>> server.start()
    """
    app = Quart(__name__)
    
    # 添加 CORS 中间件
    @app.after_request
    def after_request(response: Response) -> Response:
        return _add_cors_headers(response, cors_origins)
    
    # 处理 OPTIONS 预检请求
    @app.route('/', methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    async def handle_options(path: str = '') -> Response:
        response = Response()
        return _add_cors_headers(response, cors_origins)
    
    # 注册所有路由
    register_routes(app)
    
    return app


def register_routes(app: Any) -> None:
    """
    注册插件 Web 路由到 AstrBot 应用
    
    Args:
        app: Quart 应用实例（来自 context.app）
    
    功能：
        1. 注册后端 API 路由（/api/iris/*）
        2. 托管前端静态资源（/iris/*）
    
    访问路径：
        - API: /api/iris/memory/l2/search
        - 前端: /iris
    
    注意：
        - 实际访问地址取决于服务器配置（独立端口或 AstrBot 主端口）
        - 前端构建产物需放在 frontend/dist/ 目录
        - SPA路由：所有 /iris/* 路径返回 index.html
    """
    # 1. 注册 API 路由
    api_bp = Blueprint('iris_api', __name__)
    
    # 注册子路由
    api_bp.register_blueprint(memory_bp, url_prefix='/memory')
    api_bp.register_blueprint(profile_bp, url_prefix='/profile')
    api_bp.register_blueprint(stats_bp, url_prefix='/stats')
    
    # 注册到主应用
    app.register_blueprint(api_bp, url_prefix='/api/iris')
    
    # 2. 托管前端静态资源（SPA）
    frontend_dist = Path(__file__).parent / 'frontend' / 'dist'
    
    if frontend_dist.exists():
        @app.route('/iris', defaults={'path': 'index.html'})
        @app.route('/iris/', defaults={'path': 'index.html'})
        @app.route('/iris/<path:path>')
        async def serve_iris_frontend(path: str):
            """
            提供前端单页面应用
            
            所有 /iris/* 路径都返回对应的静态文件，
            对于前端路由路径，返回 index.html
            """
            # 检查文件是否存在
            file_path = frontend_dist / path
            if file_path.exists() and file_path.is_file():
                # 返回静态文件（JS、CSS、图片等）
                return await send_from_directory(str(frontend_dist), path)
            else:
                # 对于前端路由路径，返回 index.html
                return await send_from_directory(str(frontend_dist), 'index.html')
    else:
        logger.warning(
            f"⚠️ 前端构建产物不存在：{frontend_dist}\n"
            "   请运行：cd iris_memory/web/frontend && npm run build"
        )
