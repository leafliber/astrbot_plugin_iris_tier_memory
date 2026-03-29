"""
测试记忆重排序器
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from iris_memory.l2_memory.models import MemoryEntry, MemorySearchResult
from iris_memory.enhancement.reranker import MemoryReranker


def create_memory_result(content: str) -> MemorySearchResult:
    """创建测试用的记忆检索结果"""
    entry = MemoryEntry(
        id=f"mem_{hash(content)}",
        content=content,
        metadata={}
    )
    return MemorySearchResult(entry=entry, score=0.9, distance=0.1)


class TestMemoryReranker:
    """记忆重排序器测试"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """创建模拟的 LLM 管理器"""
        manager = MagicMock()
        manager.is_available = True
        manager.generate = AsyncMock(return_value="1. 评分：8\n2. 评分：5\n3. 评分：9")
        return manager
    
    @pytest.fixture
    def mock_config(self):
        """创建模拟的配置"""
        config = MagicMock()
        config.get = MagicMock(side_effect=lambda key, default=None: {
            "enhancement.enable_rerank": True,
        }.get(key, default))
        return config
    
    @pytest.mark.asyncio
    async def test_rerank_disabled(self, mock_llm_manager):
        """测试重排序未启用"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=False)
            mock_get_config.return_value = mock_config
            
            reranker = MemoryReranker(mock_llm_manager)
            
            memories = [create_memory_result("测试记忆")]
            reranked = await reranker.rerank(memories, query="测试查询")
            
            # 验证返回原始记忆
            assert reranked == memories
    
    @pytest.mark.asyncio
    async def test_rerank_llm_unavailable(self, mock_llm_manager):
        """测试 LLM 管理器不可用"""
        mock_llm_manager.is_available = False
        
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config
            
            reranker = MemoryReranker(mock_llm_manager)
            
            memories = [create_memory_result("测试记忆")]
            reranked = await reranker.rerank(memories, query="测试查询")
            
            # 验证返回原始记忆
            assert reranked == memories
    
    @pytest.mark.asyncio
    async def test_rerank_basic(self, mock_llm_manager):
        """测试基础重排序"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config
            
            reranker = MemoryReranker(mock_llm_manager)
            
            memories = [
                create_memory_result("用户喜欢吃苹果"),
                create_memory_result("用户今天去了超市"),
                create_memory_result("用户喜欢编程"),
            ]
            
            reranked = await reranker.rerank(memories, query="用户喜欢什么")
            
            # 验证重排序成功
            assert len(reranked) == 3
            
            # 验证调用了 LLM
            mock_llm_manager.generate.assert_called_once()
            
            # 验证 prompt 包含查询和记忆
            call_args = mock_llm_manager.generate.call_args
            prompt = call_args[1]['prompt']
            assert "用户喜欢什么" in prompt
            assert "用户喜欢吃苹果" in prompt
    
    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self, mock_llm_manager):
        """测试带 top_k 的重排序"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config
            
            reranker = MemoryReranker(mock_llm_manager)
            
            memories = [
                create_memory_result("记忆1"),
                create_memory_result("记忆2"),
                create_memory_result("记忆3"),
            ]
            
            reranked = await reranker.rerank(memories, query="测试查询", top_k=2)
            
            # 验证只返回前 2 条
            assert len(reranked) == 2
    
    @pytest.mark.asyncio
    async def test_rerank_exception_handling(self, mock_llm_manager):
        """测试异常处理"""
        mock_llm_manager.generate = AsyncMock(side_effect=Exception("LLM 调用失败"))
        
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get = MagicMock(return_value=True)
            mock_get_config.return_value = mock_config
            
            reranker = MemoryReranker(mock_llm_manager)
            
            memories = [create_memory_result("测试记忆")]
            reranked = await reranker.rerank(memories, query="测试查询")
            
            # 验证异常被捕获，返回原始记忆
            assert reranked == memories
    
    def test_build_rerank_prompt(self, mock_llm_manager):
        """测试构建重排序 Prompt"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            reranker = MemoryReranker(mock_llm_manager)
            
            memories = [
                create_memory_result("用户喜欢吃苹果"),
                create_memory_result("用户今天去了超市"),
            ]
            
            prompt = reranker._build_rerank_prompt(memories, query="用户喜欢什么")
            
            # 验证 prompt 包含必要信息
            assert "用户喜欢什么" in prompt
            assert "用户喜欢吃苹果" in prompt
            assert "用户今天去了超市" in prompt
            assert "评分" in prompt
    
    def test_build_rerank_prompt_with_long_content(self, mock_llm_manager):
        """测试长内容的 Prompt 构建"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            reranker = MemoryReranker(mock_llm_manager)
            
            # 创建超长内容的记忆
            long_content = "这是一条非常长的记忆内容，" * 100
            memories = [create_memory_result(long_content)]
            
            prompt = reranker._build_rerank_prompt(memories, query="测试查询")
            
            # 验证长内容被截断
            assert len(prompt) < len(long_content) + 1000
    
    def test_parse_scores_valid_format(self, mock_llm_manager):
        """测试解析有效格式的评分"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            reranker = MemoryReranker(mock_llm_manager)
            
            response = """
1. 评分：8
2. 评分：5
3. 评分：9
"""
            
            scores = reranker._parse_scores(response, expected_count=3)
            
            # 验证解析正确
            assert scores == [8.0, 5.0, 9.0]
    
    def test_parse_scores_with_floats(self, mock_llm_manager):
        """测试解析浮点数评分"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            reranker = MemoryReranker(mock_llm_manager)
            
            response = """
1. 评分：8.5
2. 评分：5.2
"""
            
            scores = reranker._parse_scores(response, expected_count=2)
            
            # 验证解析正确
            assert scores == [8.5, 5.2]
    
    def test_parse_scores_invalid_format(self, mock_llm_manager):
        """测试解析无效格式的评分"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            reranker = MemoryReranker(mock_llm_manager)
            
            # 无效格式
            response = "这是一些无关的文本"
            
            scores = reranker._parse_scores(response, expected_count=3)
            
            # 验证使用默认分数
            assert scores == [5.0, 5.0, 5.0]
    
    def test_parse_scores_out_of_range(self, mock_llm_manager):
        """测试超出范围的评分"""
        with patch('iris_memory.enhancement.reranker.get_config') as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            reranker = MemoryReranker(mock_llm_manager)
            
            # 超出范围的评分
            response = """
1. 评分：15
2. 评分：-5
"""
            
            scores = reranker._parse_scores(response, expected_count=2)
            
            # 验证分数被限制在范围内
            assert scores[0] == 10.0  # 最大值
            assert scores[1] == 0.0   # 最小值
