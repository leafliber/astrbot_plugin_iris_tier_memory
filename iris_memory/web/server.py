"""
独立 HTTP 服务器管理器

使用 Hypercorn 运行 Quart 应用，支持：
- 后台线程启动
- 优雅关闭
- 配置驱动
- 端口占用检测
"""
import asyncio
import socket
import threading
from typing import Optional, cast
from quart import Quart
from hypercorn.config import Config
from hypercorn.asyncio import serve

from iris_memory.core import get_logger

logger = get_logger("web.server")


def create_web_server_from_config() -> Optional['WebServer']:
    """从配置创建 Web 服务器实例
    
    自动从用户配置和隐藏配置中读取所有参数：
    - 用户配置：web.enable, web.host, web.port
    - 隐藏配置：web_ssl_cert, web_ssl_key, web_cors_origins
    
    Returns:
        WebServer 实例，如果 web.enable=False 则返回 None
    
    Example:
        >>> from iris_memory.web import create_web_server_from_config
        >>> server = create_web_server_from_config()
        >>> if server:
        >>>     server.start()
    """
    try:
        # 延迟导入避免循环依赖
        from iris_memory.config import get_config
        
        config = get_config()
        
        # 检查是否启用
        if not config.get("web.enable", True):
            logger.info("Web 服务器已禁用（web.enable=false）")
            return None
        
        # 从用户配置获取基础参数
        host = cast(str, config.get("web.host", "0.0.0.0"))
        port = cast(int, config.get("web.port", 9967))
        
        # 从隐藏配置获取安全增强参数
        ssl_cert = cast(str, config.get("web_ssl_cert", ""))
        ssl_key = cast(str, config.get("web_ssl_key", ""))
        cors_origins = cast(str, config.get("web_cors_origins", "*"))
        
        # 转换空字符串为 None
        ssl_cert = ssl_cert if ssl_cert.strip() else None
        ssl_key = ssl_key if ssl_key.strip() else None
        
        # 创建服务器实例
        server = WebServer(
            port=port,
            host=host,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key,
            cors_origins=cors_origins
        )
        
        return server
    
    except Exception as e:
        logger.error(f"创建 Web 服务器失败：{e}", exc_info=True)
        return None


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
    
    def __init__(self, port: int, host: str = "0.0.0.0", 
                 ssl_cert: Optional[str] = None, ssl_key: Optional[str] = None,
                 cors_origins: str = "*"):
        """初始化服务器
        
        Args:
            port: 监听端口
            host: 监听地址，默认 0.0.0.0（允许外部访问）
            ssl_cert: SSL 证书路径（可选）
            ssl_key: SSL 私钥路径（可选）
            cors_origins: CORS 允许的源（逗号分隔）
        """
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.cors_origins = cors_origins
        self.app: Optional[Quart] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _is_port_available(self) -> bool:
        """检查端口是否可用
        
        Returns:
            端口可用返回 True，否则返回 False
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((self.host, self.port))
                return result != 0
        except socket.error:
            return True
    
    def start(self) -> None:
        """启动服务器（后台线程）
        
        创建 Quart 应用并在 daemon 线程中启动 Hypercorn。
        如果应用未初始化，会自动调用 create_app()。
        """
        if self._thread and self._thread.is_alive():
            logger.warning("WebServer 已在运行中")
            return
        
        if not self._is_port_available():
            logger.error(f"端口 {self.port} 已被占用，Web 服务器启动失败")
            logger.error(f"请检查是否有其他实例正在运行，或更改配置中的 web.port")
            return
        
        from . import create_app
        self.app = create_app(cors_origins=self.cors_origins)
        
        self._shutdown_event = asyncio.Event()
        
        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="IrisWebServer"
        )
        self._thread.start()
        
        protocol = "https" if self.ssl_cert and self.ssl_key else "http"
        display_host = "localhost" if self.host == "0.0.0.0" else self.host
        logger.info(f"✅ Web 管理界面: {protocol}://{display_host}:{self.port}/iris")
    
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
            
            # SSL 配置
            if self.ssl_cert and self.ssl_key:
                config.certfile = self.ssl_cert
                config.keyfile = self.ssl_key
                logger.info(f"✅ 已启用 HTTPS（证书: {self.ssl_cert}）")
            
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
