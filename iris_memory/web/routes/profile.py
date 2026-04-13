"""
画像相关 API 路由

提供群聊画像和用户画像的管理接口：
- 群聊画像：查看和编辑
- 用户画像：查看和编辑
"""
from quart import Blueprint, jsonify, request
from iris_memory.web.auth import dashboard_auth
from iris_memory.core import get_component_manager, get_logger
from iris_memory.profile.models import profile_to_dict
from typing import Any, Optional, Tuple
import os

logger = get_logger("web.profile")
profile_bp = Blueprint('profile', __name__)

DEBUG_MODE = os.environ.get('IRIS_DEBUG', '').lower() in ('true', '1', 'yes')


def get_profile_storage() -> Tuple[Optional[Any], Optional[Tuple]]:
    """获取画像存储组件
    
    Returns:
        (storage, error_response): 组件和错误响应元组
        如果组件可用，返回 (storage, None)
        如果组件不可用，返回 (None, (response, status_code))
    """
    manager = get_component_manager()
    storage = manager.get_component("profile")
    
    if not storage or not storage.is_available:
        return None, (jsonify({
            'success': False,
            'error': '画像系统不可用'
        }), 503)
    
    return storage, None


def handle_exception(e: Exception, operation: str) -> Tuple[Any, int]:
    """统一异常处理
    
    Args:
        e: 异常对象
        operation: 操作描述
    
    Returns:
        (response, status_code)
    """
    logger.error(f"{operation}失败：{e}", exc_info=True)
    
    if DEBUG_MODE:
        error_msg = str(e)
    else:
        error_msg = "服务器内部错误"
    
    return jsonify({
        'success': False,
        'error': error_msg
    }), 500


@profile_bp.route('/group/<group_id>', methods=['GET'])
@dashboard_auth.require_auth
async def get_group_profile(group_id: str):
    """
    获取群聊画像
    
    Path Params:
        group_id: 群聊ID
    
    Response:
        {
            "success": true,
            "profile": {
                "group_id": "123456",
                "group_name": "测试群",
                "interests": ["游戏", "技术"],
                "atmosphere_tags": ["友好活跃", "技术范"],
                "long_term_tags": ["技术交流群"],
                "blacklist_topics": ["政治"],
                "custom_fields": {},
                "version": 1
            }
        }
    """
    try:
        profile_storage, error = get_profile_storage()
        if error:
            return error
        
        profile = await profile_storage.get_group_profile(group_id)
        
        if not profile:
            return jsonify({
                'success': True,
                'profile': {}
            })
        
        profile_data = profile_to_dict(profile)
        
        logger.info(f"获取群聊画像成功：group_id={group_id}")
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
    
    except Exception as e:
        return handle_exception(e, "获取群聊画像")


@profile_bp.route('/group/<group_id>', methods=['PUT'])
@dashboard_auth.require_auth
async def update_group_profile(group_id: str):
    """
    更新群聊画像
    
    Path Params:
        group_id: 群聊ID
    
    Request Body:
        {
            "group_name": "测试群",
            "interests": ["游戏", "技术"],
            "atmosphere_tags": ["友好活跃"],
            "long_term_tags": ["技术交流群"],
            "blacklist_topics": ["政治"]
        }
    
    Response:
        {
            "success": true,
            "message": "画像已更新"
        }
    """
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        profile_storage, error = get_profile_storage()
        if error:
            return error
        
        success = await profile_storage.update_group_profile(group_id, data)
        
        if success:
            logger.info(f"更新群聊画像成功：group_id={group_id}")
            return jsonify({
                'success': True,
                'message': '画像已更新'
            })
        else:
            return jsonify({
                'success': False,
                'error': '更新失败'
            }), 500
    
    except Exception as e:
        return handle_exception(e, "更新群聊画像")


@profile_bp.route('/user/<user_id>', methods=['GET'])
@dashboard_auth.require_auth
async def get_user_profile(user_id: str):
    """
    获取用户画像
    
    Path Params:
        user_id: 用户ID
    
    Query Params:
        group_id: 群聊ID（可选）
    
    Response:
        {
            "success": true,
            "profile": {
                "user_id": "user123",
                "user_name": "小明",
                "historical_names": ["旧昵称"],
                "personality_tags": ["开朗", "幽默"],
                "interests": ["编程", "游戏"],
                "occupation": "程序员",
                "language_style": "简洁",
                "bot_relationship": "助手",
                "important_dates": [],
                "taboo_topics": [],
                "important_events": [],
                "custom_fields": {},
                "version": 1
            }
        }
    """
    try:
        group_id = request.args.get('group_id')
        
        profile_storage, error = get_profile_storage()
        if error:
            return error
        
        profile = await profile_storage.get_user_profile(user_id, group_id)
        
        if not profile:
            return jsonify({
                'success': True,
                'profile': {}
            })
        
        profile_data = profile_to_dict(profile)
        
        logger.info(f"获取用户画像成功：user_id={user_id}, group_id={group_id}")
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
    
    except Exception as e:
        return handle_exception(e, "获取用户画像")


@profile_bp.route('/user/<user_id>', methods=['PUT'])
@dashboard_auth.require_auth
async def update_user_profile(user_id: str):
    """
    更新用户画像
    
    Path Params:
        user_id: 用户ID
    
    Query Params:
        group_id: 群聊ID（可选）
    
    Request Body:
        {
            "user_name": "小明",
            "personality_tags": ["开朗", "幽默"],
            "interests": ["编程", "游戏"],
            "occupation": "程序员",
            "language_style": "简洁",
            "bot_relationship": "助手"
        }
    
    Response:
        {
            "success": true,
            "message": "画像已更新"
        }
    """
    try:
        group_id = request.args.get('group_id')
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        profile_storage, error = get_profile_storage()
        if error:
            return error
        
        success = await profile_storage.update_user_profile(
            user_id=user_id,
            group_id=group_id or "default",
            updates=data
        )
        
        if success:
            logger.info(f"更新用户画像成功：user_id={user_id}, group_id={group_id}")
            return jsonify({
                'success': True,
                'message': '画像已更新'
            })
        else:
            return jsonify({
                'success': False,
                'error': '更新失败'
            }), 500
    
    except Exception as e:
        return handle_exception(e, "更新用户画像")


@profile_bp.route('/groups', methods=['GET'])
@dashboard_auth.require_auth
async def list_group_profiles():
    """
    获取所有群聊画像列表
    
    Response:
        {
            "success": true,
            "groups": [
                {
                    "group_id": "123456",
                    "group_name": "测试群",
                    "member_count": 50
                }
            ]
        }
    """
    try:
        profile_storage, error = get_profile_storage()
        if error:
            return error
        
        groups = await profile_storage.list_groups()
        
        return jsonify({
            'success': True,
            'groups': groups
        })
    
    except Exception as e:
        return handle_exception(e, "获取群聊列表")


@profile_bp.route('/users', methods=['GET'])
@dashboard_auth.require_auth
async def list_user_profiles():
    """
    获取用户画像列表
    
    Query Params:
        group_id: 群聊ID（可选，默认为 default）
    
    Response:
        {
            "success": true,
            "users": [
                {
                    "user_id": "user123",
                    "nickname": "小明",
                    "group_id": "123456"
                }
            ]
        }
    """
    try:
        group_id = request.args.get('group_id', 'default')
        
        profile_storage, error = get_profile_storage()
        if error:
            return error
        
        users = await profile_storage.list_users(group_id)
        
        return jsonify({
            'success': True,
            'users': users
        })
    
    except Exception as e:
        return handle_exception(e, "获取用户列表")
