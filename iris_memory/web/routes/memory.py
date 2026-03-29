"""
记忆相关 API 路由

提供L1/L2/L3三层记忆的访问接口：
- L1 Buffer: 消息缓冲列表
- L2 Memory: 记忆搜索
- L3 KG: 知识图谱数据
"""
from quart import Blueprint, jsonify, request
from iris_memory.web.auth import dashboard_auth
from iris_memory.core import get_component_manager, get_logger
from typing import Dict, Any, List

logger = get_logger("web.memory")
memory_bp = Blueprint('memory', __name__)


@memory_bp.route('/l2/search', methods=['POST'])
@dashboard_auth.require_auth
async def search_l2_memory():
    """
    搜索 L2 记忆
    
    Request Body:
        {
            "query": "搜索关键词",
            "group_id": "群聊ID（可选）",
            "top_k": 10
        }
    
    Response:
        {
            "success": true,
            "results": [
                {
                    "content": "记忆内容",
                    "score": 0.95,
                    "metadata": {},
                    "timestamp": "2026-03-29T12:00:00"
                }
            ]
        }
    """
    try:
        data = await request.get_json()
        query = data.get('query', '')
        group_id = data.get('group_id')
        top_k = data.get('top_k', 10)
        
        # 参数验证
        if not query:
            return jsonify({
                'success': False,
                'error': '搜索关键词不能为空'
            }), 400
        
        # 获取L2检索器
        manager = get_component_manager()
        l2_retriever = manager.get_component("l2_memory")
        
        if not l2_retriever or not l2_retriever.is_available:
            return jsonify({
                'success': False,
                'error': 'L2 记忆库不可用'
            }), 503
        
        # 执行搜索
        results = await l2_retriever.retrieve(query, group_id, top_k)
        
        # 格式化响应
        formatted_results = [
            {
                'content': r.content,
                'score': r.score,
                'metadata': r.metadata,
                'timestamp': r.metadata.get('timestamp')
            }
            for r in results
        ]
        
        logger.info(f"搜索L2记忆成功：查询='{query[:20]}...', 结果数={len(results)}")
        
        return jsonify({
            'success': True,
            'results': formatted_results
        })
    
    except Exception as e:
        logger.error(f"搜索 L2 记忆失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@memory_bp.route('/l1/list', methods=['GET'])
@dashboard_auth.require_auth
async def list_l1_buffer():
    """
    获取 L1 缓冲列表
    
    Query Params:
        group_id: 群聊ID（可选）
    
    Response:
        {
            "success": true,
            "messages": [
                {
                    "role": "user",
                    "content": "消息内容",
                    "timestamp": "2026-03-29T12:00:00"
                }
            ],
            "count": 10
        }
    """
    try:
        group_id = request.args.get('group_id')
        
        # 获取L1缓冲
        manager = get_component_manager()
        l1_buffer = manager.get_component("l1_buffer")
        
        if not l1_buffer or not l1_buffer.is_available:
            return jsonify({
                'success': False,
                'error': 'L1 缓冲不可用'
            }), 503
        
        # 获取消息列表
        messages = await l1_buffer.get_messages(group_id)
        
        # 格式化响应
        formatted_messages = [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None,
                'user_id': msg.user_id if hasattr(msg, 'user_id') else None
            }
            for msg in messages
        ]
        
        logger.info(f"获取L1缓冲成功：群聊={group_id}, 消息数={len(messages)}")
        
        return jsonify({
            'success': True,
            'messages': formatted_messages,
            'count': len(formatted_messages)
        })
    
    except Exception as e:
        logger.error(f"获取 L1 缓冲失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@memory_bp.route('/l3/graph', methods=['GET'])
@dashboard_auth.require_auth
async def get_l3_graph():
    """
    获取 L3 知识图谱数据
    
    Query Params:
        group_id: 群聊ID（可选）
    
    Response:
        {
            "success": true,
            "nodes": [
                {
                    "id": "node_id",
                    "label": "Person",
                    "name": "节点名称",
                    "confidence": 0.95
                }
            ],
            "edges": [
                {
                    "source": "node1",
                    "target": "node2",
                    "relation": "KNOWS"
                }
            ]
        }
    """
    try:
        group_id = request.args.get('group_id')
        
        # 获取L3图谱适配器
        manager = get_component_manager()
        l3_adapter = manager.get_component("l3_kg")
        
        if not l3_adapter or not l3_adapter.is_available:
            return jsonify({
                'success': False,
                'error': 'L3 知识图谱不可用'
            }), 503
        
        # 获取图谱数据（需要实现get_graph_data方法）
        # TODO: 在L3KGAdapter中实现get_graph_data方法
        nodes = []
        edges = []
        
        # 暂时返回空数据
        logger.info(f"获取L3图谱成功：群聊={group_id}, 节点数={len(nodes)}, 边数={len(edges)}")
        
        return jsonify({
            'success': True,
            'nodes': nodes,
            'edges': edges
        })
    
    except Exception as e:
        logger.error(f"获取 L3 图谱失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@memory_bp.route('/l2/stats', methods=['GET'])
@dashboard_auth.require_auth
async def get_l2_stats():
    """
    获取 L2 记忆库统计信息
    
    Response:
        {
            "success": true,
            "stats": {
                "total_count": 1000,
                "group_count": 10
            }
        }
    """
    try:
        manager = get_component_manager()
        l2_retriever = manager.get_component("l2_memory")
        
        if not l2_retriever or not l2_retriever.is_available:
            return jsonify({
                'success': False,
                'error': 'L2 记忆库不可用'
            }), 503
        
        # 获取统计信息（需要实现get_stats方法）
        # TODO: 在MemoryRetriever中实现get_stats方法
        stats = {
            'total_count': 0,
            'group_count': 0
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        logger.error(f"获取 L2 统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
