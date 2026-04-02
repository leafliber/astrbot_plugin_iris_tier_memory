"""
简单口令认证中间件

认证逻辑：
1. 从配置读取 access_key
2. 如果 access_key 为空，则不需要认证
3. 如果 access_key 有值，则需要验证口令

验证方式：
- Cookie: iris_access_key（优先）
- URL 参数: key
- Header: X-Access-Key
"""
from quart import request, jsonify
from functools import wraps
from typing import Optional
from iris_memory.core import get_logger

logger = get_logger("web.auth")


def get_access_key() -> Optional[str]:
    """从配置获取访问密钥
    
    Returns:
        访问密钥，如果为空则不需要认证
    """
    try:
        from iris_memory.config import get_config
        config = get_config()
        key = config.get("web.access_key", "")
        return key.strip() if key else None
    except Exception as e:
        logger.warning(f"获取访问密钥配置失败: {e}")
        return None


def verify_access_key(provided_key: str) -> bool:
    """验证访问密钥
    
    Args:
        provided_key: 用户提供的密钥
        
    Returns:
        是否验证通过
    """
    expected_key = get_access_key()
    
    if not expected_key:
        return True
    
    if not provided_key:
        return False
    
    return provided_key == expected_key


def require_auth(f):
    """认证装饰器
    
    用法：
        @require_auth
        async def protected_route():
            # 已认证
            pass
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        expected_key = get_access_key()
        
        if not expected_key:
            return await f(*args, **kwargs)
        
        provided_key = None
        
        if request.cookies.get('iris_access_key'):
            provided_key = request.cookies.get('iris_access_key')
        
        if not provided_key and request.args.get('key'):
            provided_key = request.args.get('key')
        
        if not provided_key and request.headers.get('X-Access-Key'):
            provided_key = request.headers.get('X-Access-Key')
        
        if not verify_access_key(provided_key):
            return jsonify({
                'success': False,
                'error': '访问密钥无效或未提供',
                'code': 'UNAUTHORIZED'
            }), 401
        
        return await f(*args, **kwargs)
    
    return decorated


dashboard_auth = type('DashboardAuth', (), {
    'require_auth': staticmethod(require_auth),
    'get_access_key': staticmethod(get_access_key),
    'verify_access_key': staticmethod(verify_access_key)
})()
