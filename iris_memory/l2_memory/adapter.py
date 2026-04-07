"""
Iris Tier Memory - L2 记忆库 ChromaDB 适配器

实现 L2 记忆库的存储和检索功能，支持：
- ChromaDB 向量存储
- 群聊隔离检索
- 人格隔离（collection 命名空间）
- 去重检查
- 超时保护
- 自动降级
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

from iris_memory.core import Component, get_logger
from iris_memory.config import get_config
from .models import MemoryEntry, MemorySearchResult

logger = get_logger("l2_memory.adapter")

# ChromaDB 导入（延迟导入以支持降级）
_chromadb = None
_embedding_functions = None


def _ensure_chromadb():
    """确保 ChromaDB 可用
    
    延迟导入 ChromaDB，支持降级模式。
    
    Raises:
        ImportError: ChromaDB 未安装
    """
    global _chromadb, _embedding_functions
    if _chromadb is None:
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            _chromadb = chromadb
            _embedding_functions = embedding_functions
        except ImportError as e:
            logger.error(f"ChromaDB 未安装：{e}")
            raise


class L2MemoryAdapter(Component):
    """L2 记忆库适配器
    
    使用 ChromaDB 存储和检索记忆向量。
    
    Features:
        - 群聊隔离：通过 metadata 中的 group_id 筛选
        - 人格隔离：使用人格 ID 作为 collection 名称
        - 去重检查：写入前检查相似度
        - 超时保护：检索超时后返回空列表
        - 自动降级：初始化失败时禁用模块
    
    Attributes:
        _client: ChromaDB 客户端
        _collection: 当前使用的 collection
        _embedding_func: 嵌入函数
        _persist_dir: 数据持久化目录
        _persona_id: 当前人格 ID
    """
    
    def __init__(self, persona_id: str = "default"):
        """初始化适配器
        
        Args:
            persona_id: 人格 ID，用于隔离不同人格的记忆
        """
        super().__init__()
        self._client = None
        self._collection = None
        self._embedding_func = None
        self._persist_dir: Optional[Path] = None
        self._persona_id = persona_id
        self._similarity_threshold = 0.95  # 去重相似度阈值
    
    @property
    def name(self) -> str:
        """组件名称
        
        Returns:
            "l2_memory"
        """
        return "l2_memory"
    
    async def initialize(self) -> None:
        """初始化适配器
        
        创建 ChromaDB 客户端和 collection。
        如果初始化失败，设置 _is_available = False。
        """
        config = get_config()
        
        # 检查是否启用
        if not config.get("l2_memory.enable"):
            logger.info("L2 记忆库未启用，跳过初始化")
            self._is_available = False
            self._init_error = "L2 记忆库未启用"
            return
        
        try:
            # 延迟导入 ChromaDB
            _ensure_chromadb()
            
            # 设置持久化目录
            self._persist_dir = config.data_dir / "chromadb"
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建客户端（在线程池中执行）
            loop = asyncio.get_event_loop()
            self._client = await loop.run_in_executor(
                None,
                self._create_client
            )
            
            # 创建嵌入函数（使用默认的 all-MiniLM-L6-v2）
            self._embedding_func = _embedding_functions.DefaultEmbeddingFunction()
            
            # 获取或创建 collection
            collection_name = f"memory_{self._persona_id}"
            self._collection = await loop.run_in_executor(
                None,
                lambda: self._client.get_or_create_collection(
                    name=collection_name,
                    metadata={"persona_id": self._persona_id}
                )
            )
            
            self._is_available = True
            logger.info(
                f"L2 记忆库初始化成功，collection: {collection_name}，"
                f"当前条目数: {self._collection.count()}"
            )
            
        except Exception as e:
            error_msg = f"L2 记忆库初始化失败：{e}"
            logger.error(error_msg, exc_info=True)
            self._is_available = False
            self._init_error = error_msg
    
    def _create_client(self):
        """创建 ChromaDB 客户端（同步方法）
        
        Returns:
            ChromaDB 客户端实例
        """
        return _chromadb.PersistentClient(path=str(self._persist_dir))
    
    async def shutdown(self) -> None:
        """关闭适配器
        
        清理资源。
        """
        self._client = None
        self._collection = None
        self._embedding_func = None
        self._reset_state()
        logger.info("L2 记忆库已关闭")
    
    # ========================================================================
    # 记忆存储
    # ========================================================================
    
    async def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """添加记忆到库中
        
        包含去重检查，相似度超过阈值则跳过。
        
        Args:
            content: 记忆内容
            metadata: 元数据（group_id、user_id 等）
        
        Returns:
            记忆 ID，跳过时返回已有记忆的 ID
        
        Examples:
            >>> await adapter.add_memory(
            ...     "用户喜欢吃苹果",
            ...     metadata={"group_id": "group_123"}
            ... )
            "mem_abc123"
        """
        if not self._is_available:
            logger.warning("L2 记忆库不可用，跳过添加记忆")
            return None
        
        # 准备元数据
        if metadata is None:
            metadata = {}
        
        # 确保必要字段
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().isoformat()
        if "access_count" not in metadata:
            metadata["access_count"] = 0
        if "confidence" not in metadata:
            metadata["confidence"] = 0.5
        
        try:
            # 去重检查
            existing_id = await self._check_similarity(content)
            if existing_id:
                logger.debug(f"发现相似记忆，跳过存储：{content[:50]}...")
                return existing_id
            
            # 生成记忆 ID
            memory_id = f"mem_{uuid.uuid4().hex[:12]}"
            
            # 存储到 ChromaDB（在线程池中执行）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._collection.add(
                    ids=[memory_id],
                    documents=[content],
                    metadatas=[metadata]
                )
            )
            
            logger.debug(f"已添加记忆：{memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"添加记忆失败：{e}", exc_info=True)
            return None
    
    async def _check_similarity(self, content: str) -> Optional[str]:
        """检查相似记忆
        
        检索最相似的记忆，如果相似度超过阈值则返回其 ID。
        
        Args:
            content: 待检查的内容
        
        Returns:
            相似记忆的 ID，不存在时返回 None
        """
        try:
            loop = asyncio.get_event_loop()
            
            # 检索最相似的 1 条记忆
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.query(
                    query_texts=[content],
                    n_results=1
                )
            )
            
            # 检查距离
            if results["distances"] and results["distances"][0]:
                distance = results["distances"][0][0]
                # ChromaDB 使用距离而非相似度，距离越小越相似
                # 假设距离 < 0.1 表示相似度 > 0.95
                if distance < (1 - self._similarity_threshold):
                    return results["ids"][0][0]
            
            return None
            
        except Exception as e:
            logger.warning(f"相似度检查失败：{e}")
            return None
    
    # ========================================================================
    # 记忆检索
    # ========================================================================
    
    async def retrieve(
        self,
        query: str,
        group_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[MemorySearchResult]:
        """检索记忆
        
        根据查询文本检索相似记忆，支持群聊隔离筛选。
        设置超时保护，超时后返回空列表。
        
        Args:
            query: 查询文本
            group_id: 群聊 ID（可选，用于隔离检索）
            top_k: 返回数量
        
        Returns:
            检索结果列表，超时或失败时返回空列表
        
        Examples:
            >>> results = await adapter.retrieve(
            ...     "喜欢吃什么",
            ...     group_id="group_123",
            ...     top_k=5
            ... )
            >>> len(results)
            5
        """
        if not self._is_available:
            return []
        
        config = get_config()
        timeout_ms = config.get("l2_memory.timeout_ms")
        timeout_sec = timeout_ms / 1000.0
        
        try:
            # 设置超时保护
            loop = asyncio.get_event_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._search(query, group_id, top_k)
                ),
                timeout=timeout_sec
            )
            return results
            
        except asyncio.TimeoutError:
            logger.warning(f"L2 记忆检索超时（{timeout_sec}s），跳过")
            return []
        except Exception as e:
            logger.error(f"L2 记忆检索失败：{e}", exc_info=True)
            return []
    
    def _search(
        self,
        query: str,
        group_id: Optional[str],
        top_k: int
    ) -> List[MemorySearchResult]:
        """执行检索（同步方法）
        
        Args:
            query: 查询文本
            group_id: 群聊 ID
            top_k: 返回数量
        
        Returns:
            检索结果列表
        """
        # 准备查询参数
        query_params = {
            "query_texts": [query],
            "n_results": top_k
        }
        
        # 群聊隔离筛选
        if group_id:
            query_params["where"] = {"group_id": group_id}
        
        # 执行查询
        results = self._collection.query(**query_params)
        
        # 转换结果
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                entry = MemoryEntry(
                    id=memory_id,
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    embedding=results["embeddings"][0][i] if results.get("embeddings") else None
                )
                
                # 计算相似度分数（距离越小分数越高）
                distance = results["distances"][0][i] if results["distances"] else 0.0
                score = max(0.0, 1.0 - distance)
                
                search_results.append(MemorySearchResult(
                    entry=entry,
                    score=score,
                    distance=distance
                ))
        
        return search_results
    
    # ========================================================================
    # 访问更新
    # ========================================================================
    
    async def update_access(self, memory_id: str) -> bool:
        """更新记忆的访问信息
        
        增加访问次数并更新最近访问时间。
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            是否更新成功
        
        Note:
            ChromaDB 不支持直接更新 metadata，需要先删除再添加。
            此方法暂时不实现，在阶段 6 定时任务中统一处理。
        """
        if not self._is_available:
            return False
        
        try:
            # ChromaDB 不支持直接更新 metadata，需要先删除再添加
            # 1. 查询旧记录
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._collection.get(
                    ids=[memory_id],
                    include=["embeddings", "metadatas", "documents"]
                )
            )
            
            if not result['ids']:
                logger.warning(f"记忆不存在：{memory_id}")
                return False
            
            # 2. 提取旧数据
            old_embedding = result['embeddings'][0]
            old_metadata = result['metadatas'][0]
            old_document = result['documents'][0]
            
            # 3. 更新 metadata
            access_count = old_metadata.get('access_count', 0) + 1
            old_metadata['access_count'] = access_count
            old_metadata['last_access_time'] = datetime.now().isoformat()
            
            # 4. 删除旧记录
            await loop.run_in_executor(
                None,
                lambda: self._collection.delete(ids=[memory_id])
            )
            
            # 5. 添加新记录（使用相同的 ID）
            await loop.run_in_executor(
                None,
                lambda: self._collection.add(
                    ids=[memory_id],
                    embeddings=[old_embedding],
                    metadatas=[old_metadata],
                    documents=[old_document]
                )
            )
            
            logger.debug(f"记忆访问更新成功：{memory_id}，访问次数：{access_count}")
            return True
        
        except Exception as e:
            logger.error(f"更新记忆访问失败：{e}", exc_info=True)
            return False
    
    # ========================================================================
    # 容量管理
    # ========================================================================
    
    async def get_entry_count(self) -> int:
        """获取当前记忆条目数
        
        Returns:
            记忆条目数量
        """
        if not self._is_available or not self._collection:
            return 0
        
        try:
            return self._collection.count()
        except Exception as e:
            logger.error(f"获取条目数失败：{e}")
            return 0
    
    async def get_all_entries(self) -> List[MemoryEntry]:
        """获取所有记忆条目
        
        用于遗忘淘汰任务。
        
        Returns:
            所有记忆条目列表
        """
        if not self._is_available or not self._collection:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get()
            )
            
            entries = []
            if results["ids"]:
                for i, memory_id in enumerate(results["ids"]):
                    entries.append(MemoryEntry(
                        id=memory_id,
                        content=results["documents"][i],
                        metadata=results["metadatas"][i] if results["metadatas"] else {}
                    ))
            
            return entries
            
        except Exception as e:
            logger.error(f"获取所有条目失败：{e}")
            return []
    
    async def delete_entries(self, memory_ids: List[str]) -> bool:
        """批量删除记忆条目
        
        Args:
            memory_ids: 要删除的记忆 ID 列表
        
        Returns:
            是否删除成功
        """
        if not self._is_available or not memory_ids:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._collection.delete(ids=memory_ids)
            )
            
            logger.info(f"已删除 {len(memory_ids)} 条记忆")
            return True
            
        except Exception as e:
            logger.error(f"删除记忆失败：{e}", exc_info=True)
            return False
    
    async def evict_memories(self, memory_ids: List[str]) -> int:
        """淘汰记忆条目（用于定时任务）
        
        批量删除指定的记忆条目，并记录淘汰日志。
        
        Args:
            memory_ids: 要淘汰的记忆 ID 列表
        
        Returns:
            实际删除的记忆数量
        
        Examples:
            >>> deleted_count = await adapter.evict_memories(["mem_1", "mem_2"])
            >>> print(deleted_count)
            2
        """
        if not self._is_available or not memory_ids:
            return 0
        
        try:
            # 先获取要删除的记忆内容（用于日志）
            loop = asyncio.get_event_loop()
            entries_to_delete = await loop.run_in_executor(
                None,
                lambda: self._collection.get(ids=memory_ids)
            )
            
            # 执行删除
            success = await self.delete_entries(memory_ids)
            
            if success:
                # 记录淘汰日志
                if entries_to_delete["documents"]:
                    logger.info(
                        f"已淘汰 {len(memory_ids)} 条记忆：\n" +
                        "\n".join(f"  - {doc[:100]}..." for doc in entries_to_delete["documents"][:5])
                    )
                return len(memory_ids)
            
            return 0
            
        except Exception as e:
            logger.error(f"淘汰记忆失败：{e}", exc_info=True)
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取 L2 记忆库的统计信息
        
        Returns:
            统计信息字典，包含：
            - total_count: 总记忆数
            - group_count: 群聊数量
        """
        if not self._is_available or not self._collection:
            return {
                "total_count": 0,
                "group_count": 0
            }
        
        try:
            loop = asyncio.get_event_loop()
            
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get()
            )
            
            total_count = len(results["ids"]) if results["ids"] else 0
            
            group_ids = set()
            if results.get("metadatas"):
                for meta in results["metadatas"]:
                    if meta and "group_id" in meta:
                        group_ids.add(meta["group_id"])
            
            group_count = len(group_ids)
            
            return {
                "total_count": total_count,
                "group_count": group_count
            }
        
        except Exception as e:
            logger.error(f"获取L2统计失败：{e}", exc_info=True)
            return {
                "total_count": 0,
                "group_count": 0
            }
    
    async def delete_by_group(self, group_id: str) -> int:
        """删除指定群聊的所有记忆
        
        Args:
            group_id: 群聊ID
        
        Returns:
            删除的记忆数量
        """
        if not self._is_available:
            return 0
        
        try:
            loop = asyncio.get_event_loop()
            
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get(
                    where={"group_id": group_id}
                )
            )
            
            if not results["ids"]:
                logger.debug(f"群聊 {group_id} 没有记忆记录")
                return 0
            
            memory_ids = results["ids"]
            await loop.run_in_executor(
                None,
                lambda: self._collection.delete(ids=memory_ids)
            )
            
            logger.info(f"已删除群聊 {group_id} 的 {len(memory_ids)} 条记忆")
            return len(memory_ids)
            
        except Exception as e:
            logger.error(f"删除群聊记忆失败: {e}", exc_info=True)
            return 0
    
    async def delete_by_user(self, user_id: str, group_id: Optional[str] = None) -> int:
        """删除指定用户的记忆
        
        从 metadata 的 active_users 字段中筛选包含该用户的记忆。
        
        Args:
            user_id: 用户ID
            group_id: 群聊ID（可选，不指定则删除所有群聊中该用户的记忆）
        
        Returns:
            删除的记忆数量
        """
        if not self._is_available:
            return 0
        
        try:
            loop = asyncio.get_event_loop()
            
            if group_id:
                results = await loop.run_in_executor(
                    None,
                    lambda: self._collection.get(
                        where={"group_id": group_id}
                    )
                )
            else:
                results = await loop.run_in_executor(
                    None,
                    lambda: self._collection.get()
                )
            
            if not results["ids"]:
                return 0
            
            memory_ids_to_delete = []
            for i, metadata in enumerate(results["metadatas"]):
                active_users = metadata.get("active_users", "")
                if user_id in active_users.split(","):
                    memory_ids_to_delete.append(results["ids"][i])
            
            if not memory_ids_to_delete:
                logger.debug(f"用户 {user_id} 没有记忆记录")
                return 0
            
            await loop.run_in_executor(
                None,
                lambda: self._collection.delete(ids=memory_ids_to_delete)
            )
            
            logger.info(f"已删除用户 {user_id} 的 {len(memory_ids_to_delete)} 条记忆")
            return len(memory_ids_to_delete)
            
        except Exception as e:
            logger.error(f"删除用户记忆失败: {e}", exc_info=True)
            return 0
    
    async def delete_all(self) -> int:
        """删除所有记忆
        
        Returns:
            删除的记忆数量
        """
        if not self._is_available:
            return 0
        
        try:
            loop = asyncio.get_event_loop()
            
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get()
            )
            
            total_count = len(results["ids"]) if results["ids"] else 0
            
            if total_count == 0:
                return 0
            
            await loop.run_in_executor(
                None,
                lambda: self._collection.delete(
                    ids=results["ids"]
                )
            )
            
            logger.info(f"已删除所有记忆，共 {total_count} 条")
            return total_count
            
        except Exception as e:
            logger.error(f"删除所有记忆失败: {e}", exc_info=True)
            return 0
    
    # ========================================================================
    # 知识图谱处理相关
    # ========================================================================
    
    async def get_unprocessed_count(self) -> int:
        """获取未处理的知识图谱记忆数量
        
        Returns:
            未处理的记忆数量
        """
        if not self._is_available or not self._collection:
            return 0
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get()
            )
            
            count = 0
            if results.get("metadatas"):
                for meta in results["metadatas"]:
                    if meta and not meta.get("kg_processed", False):
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"获取未处理记忆数量失败: {e}", exc_info=True)
            return 0
    
    async def get_unprocessed_memories(self, limit: int = 20) -> List[MemoryEntry]:
        """获取未处理的知识图谱记忆
        
        Args:
            limit: 最大返回数量
        
        Returns:
            未处理的记忆列表
        """
        if not self._is_available or not self._collection:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get()
            )
            
            entries = []
            if results["ids"]:
                for i, memory_id in enumerate(results["ids"]):
                    meta = results["metadatas"][i] if results.get("metadatas") else {}
                    if not meta.get("kg_processed", False):
                        entries.append(MemoryEntry(
                            id=memory_id,
                            content=results["documents"][i],
                            metadata=meta
                        ))
                        if len(entries) >= limit:
                            break
            
            return entries
            
        except Exception as e:
            logger.error(f"获取未处理记忆失败: {e}", exc_info=True)
            return []
    
    async def mark_memories_processed(self, memory_ids: List[str]) -> bool:
        """标记记忆为已处理
        
        Args:
            memory_ids: 要标记的记忆 ID 列表
        
        Returns:
            是否标记成功
        """
        if not self._is_available or not memory_ids:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get(
                    ids=memory_ids,
                    include=["embeddings", "metadatas", "documents"]
                )
            )
            
            if not results['ids']:
                logger.warning("没有找到要标记的记忆")
                return False
            
            for i, memory_id in enumerate(results['ids']):
                old_embedding = results['embeddings'][i]
                old_metadata = results['metadatas'][i]
                old_document = results['documents'][i]
                
                old_metadata['kg_processed'] = True
                
                await loop.run_in_executor(
                    None,
                    lambda mid=memory_id, emb=old_embedding, meta=old_metadata, doc=old_document: 
                    self._collection.upsert(
                        ids=[mid],
                        embeddings=[emb],
                        metadatas=[meta],
                        documents=[doc]
                    )
                )
            
            logger.info(f"已标记 {len(memory_ids)} 条记忆为已处理")
            return True
            
        except Exception as e:
            logger.error(f"标记记忆失败: {e}", exc_info=True)
            return False
    
    async def get_latest_memories(
        self,
        limit: int = 20,
        group_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """获取最新记忆
        
        按时间戳倒序获取最新的记忆条目。
        
        Args:
            limit: 返回数量，默认 20
            group_id: 群聊 ID（可选，用于隔离）
        
        Returns:
            最新记忆列表
        
        Examples:
            >>> memories = await adapter.get_latest_memories(limit=10)
            >>> len(memories)
            10
        """
        if not self._is_available:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            
            query_params: Dict[str, Any] = {
                "n_results": limit * 3
            }
            
            if group_id:
                query_params["where"] = {"group_id": group_id}
            
            results = await loop.run_in_executor(
                None,
                lambda: self._collection.get(
                    include=["documents", "metadatas"],
                    **({"where": query_params["where"]} if "where" in query_params else {})
                )
            )
            
            if not results["ids"]:
                return []
            
            entries_with_time = []
            for i, memory_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                timestamp = meta.get("timestamp", "")
                entries_with_time.append({
                    "id": memory_id,
                    "content": results["documents"][i],
                    "metadata": meta,
                    "timestamp": timestamp
                })
            
            entries_with_time.sort(key=lambda x: x["timestamp"], reverse=True)
            
            search_results = []
            for entry in entries_with_time[:limit]:
                memory_entry = MemoryEntry(
                    id=entry["id"],
                    content=entry["content"],
                    metadata=entry["metadata"]
                )
                search_results.append(MemorySearchResult(
                    entry=memory_entry,
                    score=1.0,
                    distance=0.0
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"获取最新记忆失败: {e}", exc_info=True)
            return []
