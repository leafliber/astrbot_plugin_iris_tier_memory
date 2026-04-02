"""
独立认证路由

提供自动认证流程：
1. 验证 AstrBot JWT Token
2. 生成 Iris 独立 Token
3. 设置认证 Cookie
"""
from quart import Blueprint, jsonify, request, redirect, Response
from iris_memory.web.auth import dashboard_auth
from iris_memory.core import get_logger
import jwt
import time
import secrets
from typing import Optional
from pathlib import Path
import json
import os

logger = get_logger("web.auth_routes")

auth_bp = Blueprint('auth', __name__)

IRIS_JWT_SECRET: Optional[str] = None


def _get_iris_jwt_secret() -> str:
    """获取或生成 Iris JWT 密钥"""
    global IRIS_JWT_SECRET
    
    if IRIS_JWT_SECRET:
        return IRIS_JWT_SECRET
    
    secret_file = Path("data/iris_memory/iris_jwt_secret.txt")
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    
    if secret_file.exists():
        try:
            IRIS_JWT_SECRET = secret_file.read_text().strip()
            if IRIS_JWT_SECRET:
                return IRIS_JWT_SECRET
        except Exception as e:
            logger.warning(f"读取 Iris JWT 密钥失败: {e}")
    
    IRIS_JWT_SECRET = secrets.token_urlsafe(32)
    secret_file.write_text(IRIS_JWT_SECRET)
    logger.info("✅ 已生成新的 Iris JWT 密钥")
    
    return IRIS_JWT_SECRET


def generate_iris_token(username: str, expires_hours: int = 24) -> str:
    """生成 Iris JWT Token
    
    Args:
        username: 用户名
        expires_hours: 过期时间（小时）
    
    Returns:
        JWT Token
    """
    secret = _get_iris_jwt_secret()
    payload = {
        'username': username,
        'iat': int(time.time()),
        'exp': int(time.time()) + expires_hours * 3600,
        'iss': 'iris-memory'
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def verify_iris_token(token: str) -> Optional[dict]:
    """验证 Iris JWT Token
    
    Args:
        token: JWT Token
    
    Returns:
        验证成功返回 payload，失败返回 None
    """
    try:
        secret = _get_iris_jwt_secret()
        payload = jwt.decode(token, secret, algorithms=['HS256'], issuer='iris-memory')
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Iris Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Iris Token 无效: {e}")
        return None


@auth_bp.route('/login', methods=['GET'])
async def login():
    """认证入口
    
    检查请求中的 Token 并验证：
    1. URL 参数 token（来自 AstrBot Dashboard 跳转）
    2. Cookie jwt_token（已认证）
    3. Cookie iris_token（Iris 独立认证）
    
    验证成功后设置 Iris Cookie 并重定向到主页
    """
    token = request.args.get('token')
    
    iris_token = request.cookies.get('iris_token')
    if iris_token:
        payload = verify_iris_token(iris_token)
        if payload:
            return redirect('/iris')
    
    if token:
        try:
            astrbot_payload = dashboard_auth._verify_token_with_signature(token)
            username = astrbot_payload.get('username', 'admin')
            iris_token = generate_iris_token(username)
            
            response = redirect('/iris')
            response.set_cookie(
                'iris_token',
                iris_token,
                max_age=24 * 3600,
                httponly=True,
                samesite='Lax'
            )
            logger.info(f"✅ 用户 {username} 认证成功")
            return response
            
        except ValueError as e:
            logger.warning(f"Token 验证失败: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'code': 'AUTH_FAILED'
            }), 401
        except Exception as e:
            logger.error(f"认证异常: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': '认证失败',
                'code': 'AUTH_ERROR'
            }), 500
    
    return jsonify({
        'success': False,
        'error': '缺少认证参数',
        'code': 'MISSING_TOKEN',
        'hint': '请从 AstrBot Dashboard 跳转访问，或手动输入 Token'
    }), 401


@auth_bp.route('/status', methods=['GET'])
async def auth_status():
    """检查认证状态
    
    Returns:
        {
            "authenticated": true/false,
            "username": "xxx" // 如果已认证
        }
    """
    iris_token = request.cookies.get('iris_token')
    
    if iris_token:
        payload = verify_iris_token(iris_token)
        if payload:
            return jsonify({
                'authenticated': True,
                'username': payload.get('username')
            })
    
    url_token = request.args.get('token')
    if url_token:
        try:
            astrbot_payload = dashboard_auth._verify_token_with_signature(url_token)
            return jsonify({
                'authenticated': True,
                'username': astrbot_payload.get('username'),
                'can_auto_login': True
            })
        except:
            pass
    
    return jsonify({
        'authenticated': False
    })


@auth_bp.route('/logout', methods=['POST'])
async def logout():
    """登出
    
    清除 Iris 认证 Cookie
    """
    response = jsonify({'success': True, 'message': '已登出'})
    response.delete_cookie('iris_token')
    return response


@auth_bp.route('/bookmarklet.js', methods=['GET'])
async def bookmarklet():
    """生成书签脚本
    
    用户可以将此脚本添加为浏览器书签，
    在 AstrBot Dashboard 页面点击即可跳转到 Iris
    """
    iris_host = request.host
    script = f"""javascript:(function(){{var t=document.cookie.split('; ').find(r=>r.startsWith('jwt_token='));if(t){{var e=t.split('=')[1];window.location.href='http://{iris_host}/iris/auth/login?token='+e;}}else{{alert('请先登录 AstrBot Dashboard');}}}})();"""
    
    return Response(script, mimetype='application/javascript')
