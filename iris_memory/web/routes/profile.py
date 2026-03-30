"""
画像相关 API 路由

提供群聊画像和用户画像的管理接口：
- 群聊画像：查看和编辑
- 用户画像：查看和编辑
"""
from quart import Blueprint, jsonify, request
from iris_memory.web.auth import dashboard_auth
from iris_memory.core import get_component_manager, get_logger
from typing import Dict, Any

logger = get_logger("web.profile")
profile_bp = Blueprint('profile', __name__)


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
                "atmosphere": "友好活跃",
                "active_users": ["user1", "user2"],
                "topics": ["游戏", "技术"],
                "last_active_time": "2026-03-29T12:00:00"
            }
        }
    """
    try:
        # 获取画像存储组件
        manager = get_component_manager()
        profile_storage = manager.get_component("profile")
        
        if not profile_storage or not profile_storage.is_available:
            return jsonify({
                'success': False,
                'error': '画像系统不可用'
            }), 503
        
        # 获取画像
        profile = await profile_storage.get_group_profile(group_id)
        
        if not profile:
            # 返回空画像（群聊可能还没有画像数据）
            return jsonify({
                'success': True,
                'profile': {}
            })
        
        # 格式化响应
        profile_data = profile.to_dict() if hasattr(profile, 'to_dict') else profile
        
        logger.info(f"获取群聊画像成功：group_id={group_id}")
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
    
    except Exception as e:
        logger.error(f"获取群聊画像失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profile_bp.route('/group/<group_id>', methods=['PUT'])
@dashboard_auth.require_auth
async def update_group_profile(group_id: str):
    """
    更新群聊画像
    
    Path Params:
        group_id: 群聊ID
    
    Request Body:
        {
            "atmosphere": "友好活跃",
            "topics": ["游戏", "技术"]
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
        
        # 获取画像存储组件
        manager = get_component_manager()
        profile_storage = manager.get_component("profile")
        
        if not profile_storage or not profile_storage.is_available:
            return jsonify({
                'success': False,
                'error': '画像系统不可用'
            }), 503
        
        # 更新画像
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
        logger.error(f"更新群聊画像失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
                "nickname": "小明",
                "interests": ["编程", "游戏"],
                "personality_tags": ["开朗", "幽默"],
                "last_active_time": "2026-03-29T12:00:00"
            }
        }
    """
    try:
        group_id = request.args.get('group_id')
        
        # 获取画像存储组件
        manager = get_component_manager()
        profile_storage = manager.get_component("profile")
        
        if not profile_storage or not profile_storage.is_available:
            return jsonify({
                'success': False,
                'error': '画像系统不可用'
            }), 503
        
        # 获取画像
        profile = await profile_storage.get_user_profile(user_id, group_id)
        
        if not profile:
            # 返回空画像（用户可能还没有画像数据）
            return jsonify({
                'success': True,
                'profile': {}
            })
        
        # 格式化响应
        profile_data = profile.to_dict() if hasattr(profile, 'to_dict') else profile
        
        logger.info(f"获取用户画像成功：user_id={user_id}, group_id={group_id}")
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
    
    except Exception as e:
        logger.error(f"获取用户画像失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
            "nickname": "小明",
            "interests": ["编程", "游戏"]
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
        
        # 获取画像存储组件
        manager = get_component_manager()
        profile_storage = manager.get_component("profile")
        
        if not profile_storage or not profile_storage.is_available:
            return jsonify({
                'success': False,
                'error': '画像系统不可用'
            }), 503
        
        # 更新画像
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
        logger.error(f"更新用户画像失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        # 获取画像存储组件
        manager = get_component_manager()
        profile_storage = manager.get_component("profile")
        
        if not profile_storage or not profile_storage.is_available:
            return jsonify({
                'success': False,
                'error': '画像系统不可用'
            }), 503
        
        # 获取群聊列表
        groups = await profile_storage.list_groups()
        
        return jsonify({
            'success': True,
            'groups': groups
        })
    
    except Exception as e:
        logger.error(f"获取群聊列表失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
