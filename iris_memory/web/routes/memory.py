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
                'content': r.entry.content,
                'score': r.score,
                'metadata': r.entry.metadata,
                'timestamp': r.entry.metadata.get('timestamp')
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


@memory_bp.route('/l2/latest', methods=['GET'])
@dashboard_auth.require_auth
async def get_latest_l2_memories():
    """
    获取最新的 L2 记忆
    
    Query Params:
        limit: 返回数量（默认 20，可选值：10, 20, 50, 100）
        group_id: 群聊ID（可选）
    
    Response:
        {
            "success": true,
            "results": [
                {
                    "content": "记忆内容",
                    "score": 1.0,
                    "metadata": {},
                    "timestamp": "2026-03-29T12:00:00"
                }
            ]
        }
    """
    try:
        limit = request.args.get('limit', default=20, type=int)
        group_id = request.args.get('group_id')
        
        valid_limits = [10, 20, 50, 100]
        if limit not in valid_limits:
            limit = 20
        
        manager = get_component_manager()
        l2_adapter = manager.get_component("l2_memory")
        
        if not l2_adapter or not l2_adapter.is_available:
            return jsonify({
                'success': False,
                'error': 'L2 记忆库不可用'
            }), 503
        
        results = await l2_adapter.get_latest_memories(limit=limit, group_id=group_id)
        
        formatted_results = [
            {
                'content': r.entry.content,
                'score': r.score,
                'metadata': r.entry.metadata,
                'timestamp': r.entry.metadata.get('timestamp')
            }
            for r in results
        ]
        
        logger.info(f"获取最新L2记忆成功：limit={limit}, 结果数={len(results)}")
        
        return jsonify({
            'success': True,
            'results': formatted_results
        })
    
    except Exception as e:
        logger.error(f"获取最新 L2 记忆失败：{e}", exc_info=True)
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
        messages = l1_buffer.get_context(group_id)
        
        formatted_messages = [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                'user_id': msg.source if hasattr(msg, 'source') else None
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


@memory_bp.route('/l1/queues', methods=['GET'])
@dashboard_auth.require_auth
async def list_l1_queues():
    """
    获取所有群聊的 L1 缓冲统计
    
    Response:
        {
            "success": true,
            "queues": [
                {
                    "group_id": "group_123",
                    "message_count": 10,
                    "total_tokens": 500
                }
            ]
        }
    """
    try:
        manager = get_component_manager()
        l1_buffer = manager.get_component("l1_buffer")
        
        if not l1_buffer or not l1_buffer.is_available:
            return jsonify({
                'success': False,
                'error': 'L1 缓冲不可用'
            }), 503
        
        queues = l1_buffer.get_all_queues_stats()
        
        return jsonify({
            'success': True,
            'queues': queues
        })
    
    except Exception as e:
        logger.error(f"获取 L1 队列列表失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@memory_bp.route('/l3/graph', methods=['GET'])
@dashboard_auth.require_auth
async def get_l3_graph():
    """
    获取 L3 知识图谱数据（支持拓展）
    
    Query Params:
        node_id: 起始节点ID（可选，不指定则随机选择 Person 节点）
        depth: 拓展深度 1-3（可选，默认2）
        max_nodes: 最大节点数（可选，默认50）
        max_edges: 最大边数（可选，默认100）
    
    Response:
        {
            "success": true,
            "start_node": {...},
            "nodes": [...],
            "edges": [...]
        }
    """
    try:
        node_id = request.args.get('node_id')
        depth = request.args.get('depth', default=1, type=int)
        max_nodes = request.args.get('max_nodes', default=20, type=int)
        max_edges = request.args.get('max_edges', default=100, type=int)
        
        manager = get_component_manager()
        l3_adapter = manager.get_component("l3_kg")
        
        if not l3_adapter or not l3_adapter.is_available:
            return jsonify({
                'success': False,
                'error': 'L3 知识图谱不可用'
            }), 503
        
        if not node_id:
            random_node = await l3_adapter.get_random_person_node()
            if random_node:
                node_id = random_node['id']
            else:
                return jsonify({
                    'success': True,
                    'start_node': None,
                    'nodes': [],
                    'edges': [],
                    'message': '图谱中没有 Person 类型节点'
                })
        
        nodes, edges = await l3_adapter.expand_from_node(
            node_id=node_id,
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges
        )
        
        start_node = None
        for node in nodes:
            if node['id'] == node_id:
                start_node = node
                break
        
        formatted_nodes = [
            {
                'id': node['id'],
                'label': node.get('label', 'Entity'),
                'name': node.get('name', node['id']),
                'confidence': node.get('confidence', 0.5)
            }
            for node in nodes
        ]
        
        formatted_edges = [
            {
                'source': edge['source'],
                'target': edge['target'],
                'relation': edge.get('relation', 'RELATED')
            }
            for edge in edges
        ]
        
        logger.info(f"获取L3图谱成功：起始={node_id}, 深度={depth}, 节点={len(formatted_nodes)}, 边={len(formatted_edges)}")
        
        return jsonify({
            'success': True,
            'start_node': start_node,
            'nodes': formatted_nodes,
            'edges': formatted_edges
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


@memory_bp.route('/l3/search/nodes', methods=['GET'])
@dashboard_auth.require_auth
async def search_l3_nodes():
    """
    搜索 L3 知识图谱节点
    
    Query Params:
        keyword: 搜索关键词
        limit: 返回数量（默认20）
    
    Response:
        {
            "success": true,
            "nodes": [
                {
                    "id": "node_id",
                    "label": "Person",
                    "name": "节点名称",
                    "content": "节点内容",
                    "confidence": 0.9
                }
            ]
        }
    """
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', default=20, type=int)
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': '搜索关键词不能为空'
            }), 400
        
        manager = get_component_manager()
        l3_adapter = manager.get_component("l3_kg")
        
        if not l3_adapter or not l3_adapter.is_available:
            return jsonify({
                'success': False,
                'error': 'L3 知识图谱不可用'
            }), 503
        
        nodes = await l3_adapter.search_nodes(keyword, limit)
        
        logger.info(f"搜索L3节点成功：关键词='{keyword}', 结果数={len(nodes)}")
        
        return jsonify({
            'success': True,
            'nodes': nodes
        })
    
    except Exception as e:
        logger.error(f"搜索 L3 节点失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@memory_bp.route('/l3/search/edges', methods=['GET'])
@dashboard_auth.require_auth
async def search_l3_edges():
    """
    搜索 L3 知识图谱边
    
    Query Params:
        keyword: 搜索关键词
        limit: 返回数量（默认20）
    
    Response:
        {
            "success": true,
            "edges": [
                {
                    "source": {"id": "...", "label": "...", "name": "..."},
                    "target": {"id": "...", "label": "...", "name": "..."},
                    "relation": "关系类型",
                    "confidence": 0.9
                }
            ]
        }
    """
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', default=20, type=int)
        
        if not keyword:
            return jsonify({
                'success': False,
                'error': '搜索关键词不能为空'
            }), 400
        
        manager = get_component_manager()
        l3_adapter = manager.get_component("l3_kg")
        
        if not l3_adapter or not l3_adapter.is_available:
            return jsonify({
                'success': False,
                'error': 'L3 知识图谱不可用'
            }), 503
        
        edges = await l3_adapter.search_edges(keyword, limit)
        
        logger.info(f"搜索L3边成功：关键词='{keyword}', 结果数={len(edges)}")
        
        return jsonify({
            'success': True,
            'edges': edges
        })
    
    except Exception as e:
        logger.error(f"搜索 L3 边失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
