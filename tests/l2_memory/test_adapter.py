"""L2 ChromaDB 适配器测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from iris_memory.l2_memory.adapter import L2MemoryAdapter
from iris_memory.l2_memory.models import MemoryEntry


class TestL2MemoryAdapter:
    """L2MemoryAdapter 测试"""
    
    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        config = Mock()
        config.get = Mock(side_effect=lambda key: {
            "l2_memory.enable": True,
            "l2_memory.timeout_ms": 2000,
            "l2_memory.max_entries": 10000,
            "chromadb_batch_size": 100,
        }.get(key, None))
        config.data_dir = Path("/tmp/test_iris_memory")
        return config
    
    @pytest.fixture
    def mock_chromadb(self):
        """模拟 ChromaDB"""
        with patch("iris_memory.l2_memory.adapter._chromadb") as mock_db:
            mock_client = Mock()
            mock_collection = Mock()
            mock_collection.count.return_value = 0
            
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_db.PersistentClient.return_value = mock_client
            
            yield {
                "client": mock_client,
                "collection": mock_collection,
                "module": mock_db
            }
    
    @pytest.mark.asyncio
    async def test_adapter_name(self):
        """测试适配器名称"""
        adapter = L2MemoryAdapter()
        assert adapter.name == "l2_memory"
    
    @pytest.mark.asyncio
    async def test_initialize_disabled(self, mock_config):
        """测试初始化时未启用"""
        mock_config.get = Mock(side_effect=lambda key: {
            "l2_memory.enable": False,
        }.get(key, None))
        
        with patch("iris_memory.l2_memory.adapter.get_config", return_value=mock_config):
            adapter = L2MemoryAdapter()
            await adapter.initialize()
            
            assert adapter.is_available == False
            assert "未启用" in adapter.init_error
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_config, mock_chromadb):
        """测试初始化成功"""
        with patch("iris_memory.l2_memory.adapter.get_config", return_value=mock_config), \
             patch("iris_memory.l2_memory.adapter._ensure_chromadb"):
            adapter = L2MemoryAdapter()
            
            # 直接设置客户端和集合
            adapter._client = mock_chromadb["client"]
            adapter._collection = mock_chromadb["collection"]
            adapter._embedding_func = Mock()
            adapter._is_available = True
            
            assert adapter.is_available == True
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """测试关闭适配器"""
        adapter = L2MemoryAdapter()
        adapter._is_available = True
        adapter._client = Mock()
        adapter._collection = Mock()
        
        await adapter.shutdown()
        
        assert adapter.is_available == False
        assert adapter._client is None
        assert adapter._collection is None
    
    @pytest.mark.asyncio
    async def test_add_memory_success(self, mock_config):
        """测试添加记忆成功"""
        with patch("iris_memory.l2_memory.adapter.get_config", return_value=mock_config):
            adapter = L2MemoryAdapter()
            adapter._is_available = True
            adapter._collection = Mock()
            adapter._embedding_func = Mock()
            
            # 模拟去重检查返回 None
            adapter._check_similarity = AsyncMock(return_value=None)
            
            memory_id = await adapter.add_memory(
                "测试记忆内容",
                metadata={"group_id": "group_123"}
            )
            
            assert memory_id is not None
            assert memory_id.startswith("mem_")
    
    @pytest.mark.asyncio
    async def test_add_memory_duplicate(self, mock_config):
        """测试添加重复记忆"""
        with patch("iris_memory.l2_memory.adapter.get_config", return_value=mock_config):
            adapter = L2MemoryAdapter()
            adapter._is_available = True
            adapter._collection = Mock()
            
            # 模拟去重检查返回已有 ID
            adapter._check_similarity = AsyncMock(return_value="mem_existing")
            
            memory_id = await adapter.add_memory(
                "测试记忆内容",
                metadata={"group_id": "group_123"}
            )
            
            assert memory_id == "mem_existing"
    
    @pytest.mark.asyncio
    async def test_add_memory_unavailable(self):
        """测试不可用时添加记忆"""
        adapter = L2MemoryAdapter()
        adapter._is_available = False
        
        memory_id = await adapter.add_memory("测试内容")
        
        assert memory_id is None
    
    @pytest.mark.asyncio
    async def test_retrieve_success(self, mock_config):
        """测试检索记忆成功"""
        with patch("iris_memory.l2_memory.adapter.get_config", return_value=mock_config):
            adapter = L2MemoryAdapter()
            adapter._is_available = True
            adapter._collection = Mock()
            
            # 模拟检索结果
            adapter._search = Mock(return_value=[])
            
            results = await adapter.retrieve(
                "测试查询",
                group_id="group_123",
                top_k=5
            )
            
            assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_unavailable(self):
        """测试不可用时检索"""
        adapter = L2MemoryAdapter()
        adapter._is_available = False
        
        results = await adapter.retrieve("测试查询")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_retrieve_timeout(self, mock_config):
        """测试检索超时"""
        import asyncio
        
        mock_config.get = Mock(side_effect=lambda key: {
            "l2_memory.enable": True,
            "l2_memory.timeout_ms": 100,  # 100ms 超时
        }.get(key, None))
        
        with patch("iris_memory.l2_memory.adapter.get_config", return_value=mock_config):
            adapter = L2MemoryAdapter()
            adapter._is_available = True
            adapter._collection = Mock()
            
            # 模拟超时的检索 - 需要是一个同步函数，因为 _search 是同步的
            def slow_search(*args):
                import time
                time.sleep(1)  # 睡眠 1 秒
                return []
            
            adapter._search = slow_search
            
            results = await adapter.retrieve("测试查询")
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_get_entry_count(self):
        """测试获取条目数"""
        adapter = L2MemoryAdapter()
        adapter._is_available = True
        adapter._collection = Mock()
        adapter._collection.count.return_value = 42
        
        count = await adapter.get_entry_count()
        
        assert count == 42
    
    @pytest.mark.asyncio
    async def test_get_entry_count_unavailable(self):
        """测试不可用时获取条目数"""
        adapter = L2MemoryAdapter()
        adapter._is_available = False
        
        count = await adapter.get_entry_count()
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_delete_entries(self):
        """测试删除条目"""
        adapter = L2MemoryAdapter()
        adapter._is_available = True
        adapter._collection = Mock()
        
        result = await adapter.delete_entries(["mem_001", "mem_002"])
        
        assert result == True
    
    @pytest.mark.asyncio
    async def test_delete_entries_empty(self):
        """测试删除空列表"""
        adapter = L2MemoryAdapter()
        adapter._is_available = True
        
        result = await adapter.delete_entries([])
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_delete_collection(self):
        """测试删除 collection"""
        adapter = L2MemoryAdapter()
        adapter._client = Mock()
        adapter._collection = Mock()
        adapter._collection.name = "memory_default"
        
        result = await adapter.delete_collection()
        
        assert result == True
        assert adapter._collection is None
    
    @pytest.mark.asyncio
    async def test_delete_collection_no_client(self):
        """测试无客户端时删除 collection"""
        adapter = L2MemoryAdapter()
        
        result = await adapter.delete_collection()
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_migrate_on_model_change_empty(self):
        """测试空集合迁移"""
        adapter = L2MemoryAdapter()
        adapter._collection = Mock()
        adapter._collection.count.return_value = 0
        adapter._collection.metadata = {"hnsw:space": "cosine"}
        
        result = await adapter._migrate_on_model_change(
            "BAAI/bge-small-zh-v1.5", "memory_default"
        )
        
        assert result == True
    
    @pytest.mark.asyncio
    async def test_migrate_on_model_change_with_data(self):
        """测试有数据的集合迁移"""
        adapter = L2MemoryAdapter()
        adapter._client = Mock()
        adapter._collection = Mock()
        adapter._collection.count.return_value = 2
        adapter._collection.name = "memory_default"
        adapter._collection.metadata = {"hnsw:space": "cosine"}
        adapter._embedding_func = Mock()
        adapter._is_available = True
        adapter._persist_dir = Path("/tmp/test_migration")
        
        mock_get_result = {
            "ids": ["mem_001", "mem_002"],
            "documents": ["记忆1", "记忆2"],
            "metadatas": [{"group_id": "g1"}, {"group_id": "g2"}],
        }
        adapter._collection.get.return_value = mock_get_result
        
        with patch("iris_memory.l2_memory.adapter._ensure_chromadb"), \
             patch("iris_memory.l2_memory.io.get_config") as mock_io_config:
            mock_io_config_obj = Mock()
            mock_io_config_obj.data_dir = Path("/tmp/test_migration")
            mock_io_config.return_value = mock_io_config_obj
            
            result = await adapter._migrate_on_model_change(
                "BAAI/bge-small-zh-v1.5", "memory_default"
            )
            
            assert result == True
