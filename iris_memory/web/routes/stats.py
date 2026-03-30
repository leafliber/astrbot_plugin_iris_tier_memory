"""
统计相关 API 路由

提供各类统计数据：
- Token使用统计
- 记忆统计
- 知识图谱统计
"""
from quart import Blueprint, jsonify
from iris_memory.web.auth import dashboard_auth
from iris_memory.core import get_component_manager, get_logger
from typing import Dict, Any

logger = get_logger("web.stats")
stats_bp = Blueprint('stats', __name__)


def _get_uptime() -> int:
    """获取运行时间（秒）
    
    Returns:
        运行时间（秒）
    """
    try:
        return get_uptime()
    except Exception as e:
        logger.warning(f"获取运行时间失败：{e}")
        return 0


@stats_bp.route('/token', methods=['GET'])
@dashboard_auth.require_auth
async def get_token_stats():
    """
    获取 Token 使用统计
    
    Response:
        {
            "success": true,
            "stats": {
                "global": {
                    "total_input_tokens": 10000,
                    "total_output_tokens": 3000,
                    "total_calls": 50
                },
                "l1_summarizer": {
                    "total_input_tokens": 5000,
                    "total_output_tokens": 1500,
                    "total_calls": 25
                }
            }
        }
    """
    try:
        # 获取LLM管理器
        manager = get_component_manager()
        llm_manager = manager.get_component("llm_manager")
        
        if not llm_manager or not llm_manager.is_available:
            return jsonify({
                'success': False,
                'error': 'LLM 管理器不可用'
            }), 503
        
        # 获取所有模块的Token统计
        all_stats = await llm_manager.get_all_token_stats()
        
        # 格式化响应
        formatted_stats = {}
        for module, stat in all_stats.items():
            formatted_stats[module] = {
                'total_input_tokens': stat.total_input_tokens if hasattr(stat, 'total_input_tokens') else stat.get('total_input_tokens', 0),
                'total_output_tokens': stat.total_output_tokens if hasattr(stat, 'total_output_tokens') else stat.get('total_output_tokens', 0),
                'total_calls': stat.total_calls if hasattr(stat, 'total_calls') else stat.get('total_calls', 0)
            }
        
        logger.info("获取Token统计成功")
        
        return jsonify({
            'success': True,
            'stats': formatted_stats
        })
    
    except Exception as e:
        logger.error(f"获取 Token 统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/memory', methods=['GET'])
@dashboard_auth.require_auth
async def get_memory_stats():
    """
    获取记忆统计
    
    Response:
        {
            "success": true,
            "stats": {
                "l1": {
                    "queue_length": 10,
                    "max_capacity": 100
                },
                "l2": {
                    "total_count": 1000,
                    "group_count": 5
                },
                "l3": {
                    "node_count": 500,
                    "edge_count": 1000
                }
            }
        }
    """
    try:
        manager = get_component_manager()
        
        stats: Dict[str, Any] = {
            'l1': {},
            'l2': {},
            'l3': {}
        }
        
        # L1 统计
        l1_buffer = manager.get_component("l1_buffer")
        if l1_buffer and l1_buffer.is_available:
            try:
                stats['l1'] = l1_buffer.get_stats()
            except Exception as e:
                logger.warning(f"获取L1统计失败：{e}")
                stats['l1'] = {}
        
        # L2 统计
        l2_memory = manager.get_component("l2_memory")
        if l2_memory and l2_memory.is_available:
            try:
                stats['l2'] = await l2_memory.get_stats()
            except Exception as e:
                logger.warning(f"获取L2统计失败：{e}")
                stats['l2'] = {}
        
        # L3 统计
        l3_kg = manager.get_component("l3_kg")
        if l3_kg and l3_kg.is_available:
            try:
                kg_stats = await l3_kg.get_stats()
                stats['l3'] = kg_stats
            except Exception as e:
                logger.warning(f"获取L3统计失败：{e}")
                stats['l3'] = {}
        
        logger.info("获取记忆统计成功")
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"获取记忆统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/kg', methods=['GET'])
@dashboard_auth.require_auth
async def get_kg_stats():
    """
    获取知识图谱统计
    
    Response:
        {
            "success": true,
            "stats": {
                "node_count": 500,
                "edge_count": 1000,
                "node_types": {
                    "Person": 100,
                    "Event": 50
                },
                "relation_types": {
                    "KNOWS": 200,
                    "MENTIONED_IN": 150
                }
            }
        }
    """
    try:
        # 获取L3图谱适配器
        manager = get_component_manager()
        l3_adapter = manager.get_component("l3_kg")
        
        if not l3_adapter or not l3_adapter.is_available:
            return jsonify({
                'success': False,
                'error': 'L3 知识图谱不可用'
            }), 503
        
        # 获取图谱统计
        stats = await l3_adapter.get_stats()
        
        logger.info("获取图谱统计成功")
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"获取图谱统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/system', methods=['GET'])
@dashboard_auth.require_auth
async def get_system_stats():
    """
    获取系统整体统计
    
    Response:
        {
            "success": true,
            "stats": {
                "components": {
                    "l1_buffer": true,
                    "l2_memory": true,
                    "l3_kg": false,
                    "profile": true,
                    "llm_manager": true
                },
                "uptime": 3600,
                "version": "1.0.0"
            }
        }
    """
    try:
        manager = get_component_manager()
        
        # 获取各组件可用性
        components = {}
        component_names = ["l1_buffer", "l2_memory", "l3_kg", "profile", "llm_manager"]
        
        for name in component_names:
            component = manager.get_component(name)
            components[name] = component is not None and component.is_available
        
        stats = {
            'components': components,
            'uptime': _get_uptime(),
            'version': '1.0.0'
        }
        
        logger.info("获取系统统计成功")
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"获取系统统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/all', methods=['GET'])
@dashboard_auth.require_auth
async def get_all_stats():
    """
    获取所有统计数据（合并端点）
    
    一次性返回 memory、token、kg、system 四种统计数据，
    减少前端并发请求数，避免触发速率限制。
    
    Response:
        {
            "success": true,
            "data": {
                "memory": {...},
                "token": {...},
                "kg": {...},
                "system": {...}
            }
        }
    """
    try:
        manager = get_component_manager()
        
        # 1. 记忆统计
        memory_stats: Dict[str, Any] = {'l1': {}, 'l2': {}, 'l3': {}}
        
        l1_buffer = manager.get_component("l1_buffer")
        if l1_buffer and l1_buffer.is_available:
            try:
                memory_stats['l1'] = l1_buffer.get_stats()
            except Exception as e:
                logger.warning(f"获取L1统计失败：{e}")
        
        l2_memory = manager.get_component("l2_memory")
        if l2_memory and l2_memory.is_available:
            try:
                memory_stats['l2'] = await l2_memory.get_stats()
            except Exception as e:
                logger.warning(f"获取L2统计失败：{e}")
        
        l3_kg = manager.get_component("l3_kg")
        if l3_kg and l3_kg.is_available:
            try:
                memory_stats['l3'] = await l3_kg.get_stats()
            except Exception as e:
                logger.warning(f"获取L3统计失败：{e}")
        
        # 2. Token 统计
        token_stats: Dict[str, Any] = {}
        llm_manager = manager.get_component("llm_manager")
        if llm_manager and llm_manager.is_available:
            try:
                all_stats = await llm_manager.get_all_token_stats()
                for module, stat in all_stats.items():
                    token_stats[module] = {
                        'total_input_tokens': stat.total_input_tokens if hasattr(stat, 'total_input_tokens') else stat.get('total_input_tokens', 0),
                        'total_output_tokens': stat.total_output_tokens if hasattr(stat, 'total_output_tokens') else stat.get('total_output_tokens', 0),
                        'total_calls': stat.total_calls if hasattr(stat, 'total_calls') else stat.get('total_calls', 0)
                    }
            except Exception as e:
                logger.warning(f"获取Token统计失败：{e}")
        
        # 3. 知识图谱统计
        kg_stats: Dict[str, Any] = {'node_count': 0, 'edge_count': 0, 'node_types': {}, 'relation_types': {}}
        if l3_kg and l3_kg.is_available:
            try:
                kg_stats = await l3_kg.get_stats()
            except Exception as e:
                logger.warning(f"获取图谱统计失败：{e}")
        
        # 4. 系统统计
        components = {}
        for name in ["l1_buffer", "l2_memory", "l3_kg", "profile", "llm_manager"]:
            component = manager.get_component(name)
            components[name] = component is not None and component.is_available
        
        system_stats = {
            'components': components,
            'uptime': _get_uptime(),
            'version': '1.0.0'
        }
        
        logger.info("获取所有统计成功")
        
        return jsonify({
            'success': True,
            'data': {
                'memory': memory_stats,
                'token': token_stats,
                'kg': kg_stats,
                'system': system_stats
            }
        })
    
    except Exception as e:
        logger.error(f"获取所有统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
