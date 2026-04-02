"""
简单口令认证路由

提供：
- 登录验证
- 认证状态检查
- 登出
"""
from quart import Blueprint, jsonify, request, redirect, Response
from iris_memory.web.auth import get_access_key, verify_access_key
from iris_memory.core import get_logger

logger = get_logger("web.auth_routes")

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
async def login():
    """登录验证
    
    请求体：
        {
            "key": "访问密钥"
        }
    
    返回：
        成功：设置 Cookie 并返回成功
        失败：返回错误信息
    """
    data = await request.get_json(silent=True) or {}
    provided_key = data.get('key', '')
    
    expected_key = get_access_key()
    
    if not expected_key:
        response = jsonify({
            'success': True,
            'message': '无需认证'
        })
        return response
    
    if verify_access_key(provided_key):
        response = jsonify({
            'success': True,
            'message': '认证成功'
        })
        response.set_cookie(
            'iris_access_key',
            provided_key,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite='Lax'
        )
        logger.info("✅ 用户认证成功")
        return response
    else:
        logger.warning("❌ 认证失败：密钥错误")
        return jsonify({
            'success': False,
            'error': '访问密钥错误',
            'code': 'AUTH_FAILED'
        }), 401


@auth_bp.route('/status', methods=['GET'])
async def auth_status():
    """检查认证状态
    
    返回：
        {
            "require_auth": true/false,
            "authenticated": true/false
        }
    """
    expected_key = get_access_key()
    
    if not expected_key:
        return jsonify({
            'require_auth': False,
            'authenticated': True
        })
    
    provided_key = request.cookies.get('iris_access_key')
    
    if not provided_key:
        provided_key = request.args.get('key')
    
    if not provided_key:
        provided_key = request.headers.get('X-Access-Key')
    
    authenticated = verify_access_key(provided_key)
    
    return jsonify({
        'require_auth': True,
        'authenticated': authenticated
    })


@auth_bp.route('/logout', methods=['POST'])
async def logout():
    """登出
    
    清除认证 Cookie
    """
    response = jsonify({'success': True, 'message': '已登出'})
    response.delete_cookie('iris_access_key')
    return response
