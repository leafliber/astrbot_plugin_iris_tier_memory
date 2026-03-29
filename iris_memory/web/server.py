"""
独立 HTTP 服务器管理器

使用 Hypercorn 运行 Quart 应用，支持：
- 后台线程启动
- 优雅关闭
- 配置驱动
"""
import asyncio
import threading
from typing import Optional
from quart import Quart
from hypercorn.config import Config
from hypercorn.asyncio import serve

from iris_memory.core import get_logger

logger = get_logger("web.server")


class WebServer:
    """独立 HTTP 服务器管理器
    
    在后台线程中运行 Quart 应用，提供 Web API 和前端界面。
    
    Attributes:
        host: 监听地址
        port: 监听端口
        app: Quart 应用实例
        _shutdown_event: 关闭信号
        _thread: 后台线程
    
    Example:
        >>> server = WebServer(port=9967)
        >>> server.start()
        >>> # ... 插件运行 ...
        >>> server.shutdown()
    """
    
    def __init__(self, port: int, host: str = "0.0.0.0"):
        """初始化服务器
        
        Args:
            port: 监听端口
            host: 监听地址，默认 0.0.0.0（允许外部访问）
        """
        self.host = host
        self.port = port
        self.app: Optional[Quart] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info(f"WebServer 初始化: {host}:{port}")
    
    def start(self) -> None:
        """启动服务器（后台线程）
        
        创建 Quart 应用并在 daemon 线程中启动 Hypercorn。
        如果应用未初始化，会自动调用 create_app()。
        """
        if self._thread and self._thread.is_alive():
            logger.warning("WebServer 已在运行中")
            return
        
        # 延迟导入避免循环依赖
        from . import create_app
        self.app = create_app()
        
        # 创建关闭事件
        self._shutdown_event = asyncio.Event()
        
        # 启动后台线程
        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="IrisWebServer"
        )
        self._thread.start()
        
        logger.info(f"✅ Web 服务器已启动: http://{self.host}:{self.port}")
    
    def shutdown(self) -> None:
        """优雅关闭服务器
        
        触发关闭信号，等待服务器停止处理请求后退出。
        """
        if not self._shutdown_event or not self._loop:
            logger.warning("WebServer 未运行")
            return
        
        logger.info("开始关闭 Web 服务器...")
        
        # 在事件循环中触发关闭
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        
        # 等待线程结束（最多等待 5 秒）
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("WebServer 线程未能在超时时间内关闭")
            else:
                logger.info("✅ Web 服务器已关闭")
    
    def _run_server(self) -> None:
        """运行 Hypercorn 服务器（在线程中）
        
        创建新的事件循环并运行 Hypercorn ASGI 服务器。
        """
        # 为线程创建新的事件循环
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            # 配置 Hypercorn
            config = Config()
            config.bind = [f"{self.host}:{self.port}"]
            config.access_log_format = '%(h)s "%(r)s" %(s)s %(b)s'
            
            # 运行服务器（直到收到关闭信号）
            self._loop.run_until_complete(
                serve(
                    self.app,
                    config,
                    shutdown_trigger=self._shutdown_event.wait
                )
            )
        
        except Exception as e:
            logger.error(f"Web 服务器运行异常: {e}", exc_info=True)
        
        finally:
            # 清理事件循环
            self._loop.close()
            self._loop = None
