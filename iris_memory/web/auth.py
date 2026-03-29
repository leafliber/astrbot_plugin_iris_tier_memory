"""
认证中间件 - 复用 AstrBot Dashboard JWT 认证

安全策略：
1. 从AstrBot配置文件读取JWT密钥
2. 完整验证JWT签名和过期时间
3. 验证用户名是否为管理员
4. 适用于AstrBot > 3.5.17版本（修复CVE-2025-55449后）
"""
from quart import request, jsonify
from functools import wraps
import jwt
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from iris_memory.core import get_logger

logger = get_logger("web.auth")


class DashboardAuth:
    """复用 AstrBot Dashboard JWT 认证
    
    认证流程：
    1. 从Cookie或Header获取JWT Token
    2. 从AstrBot配置读取JWT密钥
    3. 验证签名、过期时间、用户身份
    4. 注入用户信息到请求上下文
    """
    
    def __init__(self):
        self.dashboard_config = self._load_dashboard_config()
        self.jwt_secret = self._load_jwt_secret()
        
        if not self.jwt_secret:
            logger.warning(
                "⚠️ 未找到JWT密钥，认证功能受限。"
                "请确保AstrBot版本 > 3.5.17"
            )
    
    def _load_dashboard_config(self) -> dict:
        """加载 AstrBot Dashboard 配置
        
        Returns:
            Dashboard配置字典
        """
        config_path = Path("data/cmd_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
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
            logger.info("✅ 已加载JWT密钥（完整签名验证）")
        else:
            logger.warning(
                "未找到JWT密钥配置，可能是旧版本AstrBot或配置文件损坏"
            )
        
        return jwt_secret
    
    def _get_token(self) -> Optional[str]:
        """从请求中获取 JWT Token
        
        优先级：
        1. Cookie中的jwt_token（浏览器访问）
        2. Header中的Authorization Bearer Token（API调用）
        
        Returns:
            JWT Token字符串，如果不存在则返回None
        """
        # 优先从Cookie获取（浏览器访问）
        token = request.cookies.get('jwt_token')
        
        # 支持从Header获取（API调用）
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
            # 获取Token
            token = self._get_token()
            
            if not token:
                return jsonify({
                    'success': False,
                    'error': '未登录，请先登录 AstrBot WebUI',
                    'code': 'UNAUTHORIZED'
                }), 401
            
            try:
                # 验证Token（完整签名验证）
                payload = self._verify_token_with_signature(token)
                
                # 注入用户信息到请求上下文
                request.current_user = payload.get('username')
                request.is_admin = True
                
                # 执行业务逻辑
                return await f(*args, **kwargs)
            
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


# 全局单例实例
dashboard_auth = DashboardAuth()
