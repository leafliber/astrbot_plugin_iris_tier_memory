"""
认证中间件 - 复用 AstrBot Dashboard JWT 认证

安全策略：
1. 从AstrBot配置文件读取JWT密钥
2. 完整验证JWT签名和过期时间
3. 验证用户名是否为管理员
4. 适用于AstrBot > 3.5.17版本（修复CVE-2025-55449后）
5. 支持速率限制防止暴力破解
6. 支持 Iris 独立 Token 认证
"""
import os
from quart import request, jsonify
from functools import wraps
import jwt
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, cast
from collections import defaultdict
import threading
from iris_memory.core import get_logger

logger = get_logger("web.auth")


class RateLimiter:
    """简单的速率限制器（基于内存）
    
    注意：生产环境建议使用 Redis 等分布式存储
    """
    
    def __init__(self, max_requests: int = None, window_seconds: int = None):
        """
        Args:
            max_requests: 时间窗口内最大请求数（None 则使用配置值）
            window_seconds: 时间窗口（秒）（None 则使用配置值）
        """
        # 延迟加载配置值（避免循环导入）
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    @property
    def max_requests(self) -> int:
        """从配置获取最大请求数"""
        if self._max_requests is not None:
            return self._max_requests
        try:
            from iris_memory.config import get_config
            config = get_config()
            return cast(int, config.get("web_rate_limit_max_requests", 20))
        except:
            return 20  # 默认值
    
    @property
    def window_seconds(self) -> int:
        """从配置获取时间窗口"""
        if self._window_seconds is not None:
            return self._window_seconds
        try:
            from iris_memory.config import get_config
            config = get_config()
            return cast(int, config.get("web_rate_limit_window_seconds", 60))
        except:
            return 60  # 默认值
    
    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """检查是否允许请求
        
        Args:
            client_id: 客户端标识（如 IP 地址）
            
        Returns:
            (是否允许, 剩余请求数)
        """
        now = time.time()
        cutoff = now - self.window_seconds
        
        with self._lock:
            # 清理过期记录
            self.requests[client_id] = [
                ts for ts in self.requests[client_id] if ts > cutoff
            ]
            
            # 检查是否超限
            if len(self.requests[client_id]) >= self.max_requests:
                return False, 0
            
            # 记录新请求
            self.requests[client_id].append(now)
            return True, self.max_requests - len(self.requests[client_id])


class DashboardAuth:
    """复用 AstrBot Dashboard JWT 认证
    
    认证流程：
    1. 从Cookie或Header获取JWT Token
    2. 从AstrBot配置读取JWT密钥
    3. 验证签名、过期时间、用户身份
    4. 注入用户信息到请求上下文
    5. 速率限制防止暴力破解
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: AstrBot 配置文件路径（可选，默认自动检测）
        """
        self.config_path = config_path or self._detect_config_path()
        self.dashboard_config = self._load_dashboard_config()
        self.jwt_secret = self._load_jwt_secret()
        self.rate_limiter = RateLimiter()  # 使用配置值
        
        if not self.jwt_secret:
            logger.error(
                "❌ JWT 密钥未配置，认证将始终失败！"
                f"配置路径: {self.config_path}，"
                "请确保 AstrBot 版本 > 3.5.17 或手动配置 jwt_secret"
            )
        else:
            logger.debug("✅ JWT 认证已就绪")
    
    def _detect_config_path(self) -> Path:
        """自动检测 AstrBot 配置文件路径
        
        Returns:
            配置文件路径
        """
        # 优先级：环境变量 > 默认路径
        env_path = os.environ.get('ASTR_BOT_CONFIG_PATH')
        if env_path:
            return Path(env_path)
        
        # 尝试常见路径
        common_paths = [
            Path("data/cmd_config.json"),  # 标准路径
            Path("../../data/cmd_config.json"),  # 相对路径
            Path("/app/data/cmd_config.json"),  # Docker 容器路径
        ]
        
        for path in common_paths:
            if path.exists():
                return path
        
        # 默认返回标准路径
        return Path("data/cmd_config.json")
    
    def _load_dashboard_config(self) -> dict:
        """加载 AstrBot Dashboard 配置
        
        Returns:
            Dashboard配置字典
        """
        config_path = Path("data/cmd_config.json")
        if config_path.exists():
            try:
                # 使用 utf-8-sig 自动处理 BOM (Byte Order Mark)
                with open(config_path, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载Dashboard配置失败：{e}")
        return {}
    
    def _load_jwt_secret(self) -> Optional[str]:
        """从AstrBot配置加载JWT密钥
        
        新版AstrBot（> 3.5.17）每次部署时随机生成JWT密钥，
        存储在data/cmd_config.json中
        
        Returns:
            JWT密钥字符串，如果不存在则返回None
        """
        # 尝试从dashboard配置中获取JWT密钥
        jwt_secret = self.dashboard_config.get('dashboard', {}).get('jwt_secret')
        
        if jwt_secret:
            logger.debug("✅ 已加载JWT密钥（完整签名验证）")
        else:
            logger.warning(
                "未找到JWT密钥配置，可能是旧版本AstrBot或配置文件损坏"
            )
        
        return jwt_secret
    
    def _get_token(self) -> Optional[str]:
        """从请求中获取 JWT Token
        
        优先级：
        1. Cookie中的jwt_token（浏览器访问）
        2. URL参数中的token（跨端口访问）
        3. Header中的Authorization Bearer Token（API调用）
        
        Returns:
            JWT Token字符串，如果不存在则返回None
        """
        token = request.cookies.get('jwt_token')
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        return token
    
    def _is_valid_admin(self, payload: dict) -> bool:
        """验证是否为有效管理员
        
        Args:
            payload: JWT Token解码后的payload
            
        Returns:
            是否为有效管理员
        """
        username = payload.get('username')
        if not username:
            return False
        
        # 从AstrBot配置获取管理员用户名
        dashboard_username = self.dashboard_config.get('dashboard', {}).get('username')
        
        if not dashboard_username:
            logger.warning("未配置Dashboard用户名")
            return False
        
        return username == dashboard_username
    
    def _is_token_expired(self, payload: dict) -> bool:
        """检查Token是否过期
        
        Args:
            payload: JWT Token解码后的payload
            
        Returns:
            Token是否已过期
        """
        exp = payload.get('exp')
        if exp:
            return time.time() > exp
        return True  # 没有过期时间字段，视为过期
    
    def _verify_token_with_signature(self, token: str) -> dict:
        """完整验证JWT签名（推荐方案）
        
        Args:
            token: JWT Token字符串
            
        Returns:
            解码后的payload
            
        Raises:
            ValueError: 验证失败时抛出
        """
        if not self.jwt_secret:
            raise ValueError(
                'JWT密钥未配置，请确保AstrBot版本 > 3.5.17 '
                '并检查data/cmd_config.json配置文件'
            )
        
        try:
            # 完整验证：签名 + 过期时间
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=['HS256']
            )
            
            # 验证管理员身份
            if not self._is_valid_admin(payload):
                raise ValueError('非管理员，无权访问')
            
            return payload
        
        except jwt.ExpiredSignatureError:
            raise ValueError('登录已过期，请重新登录')
        except jwt.InvalidTokenError as e:
            raise ValueError(f'Token无效: {str(e)}')
    
    def require_auth(self, f):
        """认证装饰器
        
        支持 Iris Token 和 AstrBot Token 双重认证：
        1. 优先检查 Iris Token（Cookie: iris_token）
        2. 其次检查 AstrBot Token（Cookie/URL参数: jwt_token）
        
        用法：
            @dashboard_auth.require_auth
            async def protected_route():
                # 已认证，可访问request.current_user
                pass
        
        Args:
            f: 被装饰的函数
            
        Returns:
            装饰后的函数
        """
        @wraps(f)
        async def decorated(*args, **kwargs):
            # 速率限制检查
            client_ip = request.remote_addr or 'unknown'
            allowed, remaining = self.rate_limiter.is_allowed(client_ip)
            
            if not allowed:
                logger.warning(f"速率限制触发: {client_ip}")
                return jsonify({
                    'success': False,
                    'error': '请求过于频繁，请稍后再试',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'retry_after': 60
                }), 429
            
            # 优先检查 Iris Token
            iris_token = request.cookies.get('iris_token')
            if iris_token:
                try:
                    from .routes.auth_routes import verify_iris_token
                    iris_payload = verify_iris_token(iris_token)
                    if iris_payload:
                        request.current_user = iris_payload.get('username')
                        request.is_admin = True
                        response = await f(*args, **kwargs)
                        if hasattr(response, 'headers'):
                            response.headers['X-RateLimit-Remaining'] = str(remaining)
                        return response
                except Exception as e:
                    logger.debug(f"Iris Token 验证失败: {e}")
            
            # 获取 AstrBot Token
            token = self._get_token()
            
            if not token:
                return jsonify({
                    'success': False,
                    'error': '未登录，请先登录 AstrBot WebUI',
                    'code': 'UNAUTHORIZED'
                }), 401
            
            # 检查 JWT 密钥是否已加载
            if not self.jwt_secret:
                logger.error("JWT 密钥未配置，拒绝访问")
                return jsonify({
                    'success': False,
                    'error': '服务器认证配置错误，请联系管理员',
                    'code': 'AUTH_CONFIG_ERROR'
                }), 500
            
            try:
                # 验证Token（完整签名验证）
                payload = self._verify_token_with_signature(token)
                
                # 注入用户信息到请求上下文
                request.current_user = payload.get('username')
                request.is_admin = True
                
                # 添加速率限制响应头
                response = await f(*args, **kwargs)
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                
                return response
            
            except ValueError as e:
                logger.warning(f"认证失败：{e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'code': 'FORBIDDEN'
                }), 403
            
            except Exception as e:
                logger.error(f"认证异常：{e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': f'认证失败: {str(e)}',
                    'code': 'AUTH_ERROR'
                }), 500
        
        return decorated
    
    def generate_csrf_token(self) -> str:
        """生成 CSRF Token
        
        Returns:
            随机生成的 CSRF Token
        """
        import secrets
        return secrets.token_urlsafe(32)
    
    def validate_csrf_token(self, token: Optional[str]) -> bool:
        """验证 CSRF Token
        
        Args:
            token: 客户端提交的 Token
            
        Returns:
            Token 是否有效
        """
        if not token:
            return False
        
        # 从 Cookie 获取 CSRF Token
        cookie_token = request.cookies.get('csrf_token')
        if not cookie_token:
            return False
        
        # 从 Header 或 Form 获取提交的 Token
        submitted_token = token or request.headers.get('X-CSRF-Token')
        
        # 常量时间比较，防止时序攻击
        import hmac
        return hmac.compare_digest(cookie_token, submitted_token or '')


def csrf_protect(f):
    """CSRF 保护装饰器
    
    用法：
        @dashboard_auth.require_auth
        @csrf_protect
        async def protected_route():
            pass
    
    注意：
        - 需要前端在请求中包含 X-CSRF-Token Header
        - Cookie 中的 csrf_token 由前端设置
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        # 仅检查 POST/PUT/DELETE 请求
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            csrf_token = request.headers.get('X-CSRF-Token') or \
                        request.json.get('csrf_token') if request.is_json else None
            
            cookie_token = request.cookies.get('csrf_token')
            
            if not csrf_token or not cookie_token:
                logger.warning(f"CSRF Token 缺失: {request.method} {request.path}")
                return jsonify({
                    'success': False,
                    'error': 'CSRF Token 缺失，请刷新页面重试',
                    'code': 'CSRF_TOKEN_MISSING'
                }), 403
            
            # 常量时间比较
            import hmac
            if not hmac.compare_digest(csrf_token, cookie_token):
                logger.warning(f"CSRF Token 不匹配: {request.method} {request.path}")
                return jsonify({
                    'success': False,
                    'error': 'CSRF Token 无效',
                    'code': 'CSRF_TOKEN_INVALID'
                }), 403
        
        return await f(*args, **kwargs)
    
    return decorated


# 全局单例实例
dashboard_auth = DashboardAuth()
