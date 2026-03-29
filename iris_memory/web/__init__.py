"""
Web 模块 - 提供前后端分离的 Web 界面

架构：
- 后端：Quart API（共享 AstrBot 端口）
- 前端：Vue.js 3 SPA（构建后由 Quart 托管）
- 认证：复用 AstrBot Dashboard JWT

使用方式：
    from iris_memory.web import register_routes
    
    # 在插件入口注册路由
    register_routes(context.app)
"""
from quart import Blueprint, send_from_directory
from pathlib import Path
from typing import Any

from .routes.memory import memory_bp
from .routes.profile import profile_bp
from .routes.stats import stats_bp
from .auth import dashboard_auth
from iris_memory.core import get_logger

logger = get_logger("web")

__all__ = ['register_routes', 'dashboard_auth']


def register_routes(app: Any) -> None:
    """
    注册插件 Web 路由到 AstrBot 应用
    
    Args:
        app: Quart 应用实例（来自 context.app）
    
    功能：
        1. 注册后端 API 路由（/api/iris/*）
        2. 托管前端静态资源（/iris/*）
    
    访问路径：
        - API: http://localhost:6185/api/iris/memory/l2/search
        - 前端: http://localhost:6185/iris
    
    注意：
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
    
    logger.info("✅ Iris Memory API 已注册到 /api/iris")
    
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
        
        logger.info("✅ Iris Memory Web 界面已挂载到 http://localhost:6185/iris")
    else:
        logger.warning(
            f"⚠️ 前端构建产物不存在：{frontend_dist}\n"
            "   请运行：cd iris_memory/web/frontend && npm run build"
        )
