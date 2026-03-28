"""总结器测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from iris_memory.l1_buffer import Summarizer, MessageQueue, ContextMessage
from iris_memory.llm.caller import PlaceholderLLMCaller


@pytest.fixture
def mock_queue():
    """创建模拟队列"""
    queue = MessageQueue(group_id="group_123")
    
    # 添加一些消息
    for i in range(5):
        msg = ContextMessage(
            role="user" if i % 2 == 0 else "assistant",
            content=f"消息{i}",
            timestamp=datetime.now(),
            token_count=10,
            source="user_456"
        )
        queue.add_message(msg)
    
    return queue


class TestSummarizer:
    """总结器测试"""
    
    def test_create_summarizer(self):
        """测试创建总结器"""
        summarizer = Summarizer()
        
        assert summarizer.llm_caller is not None
        assert isinstance(summarizer.llm_caller, PlaceholderLLMCaller)
    
    def test_create_summarizer_with_custom_caller(self):
        """测试使用自定义调用器创建"""
        custom_caller = Mock()
        summarizer = Summarizer(llm_caller=custom_caller)
        
        assert summarizer.llm_caller == custom_caller
    
    def test_should_summarize_by_length(self, mock_queue):
        """测试按消息数量触发总结"""
        with patch('iris_memory.l1_buffer.summarizer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.inject_queue_length": 3,
                "l1_buffer.max_queue_tokens": 10000
            }.get(key, None))
            
            summarizer = Summarizer()
            
            # 队列有 5 条消息，限制是 3，应该触发
            assert summarizer.should_summarize(mock_queue)
    
    def test_should_summarize_by_tokens(self, mock_queue):
        """测试按 Token 数触发总结"""
        with patch('iris_memory.l1_buffer.summarizer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.inject_queue_length": 100,
                "l1_buffer.max_queue_tokens": 40  # 队列有 50 tokens
            }.get(key, None))
            
            summarizer = Summarizer()
            
            # 队列有 50 tokens，限制是 40，应该触发
            assert summarizer.should_summarize(mock_queue)
    
    def test_should_not_summarize(self, mock_queue):
        """测试不触发总结"""
        with patch('iris_memory.l1_buffer.summarizer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.inject_queue_length": 100,
                "l1_buffer.max_queue_tokens": 10000
            }.get(key, None))
            
            summarizer = Summarizer()
            
            # 队列有 5 条消息和 50 tokens，都未超限
            assert not summarizer.should_summarize(mock_queue)
    
    @pytest.mark.asyncio
    async def test_summarize_with_placeholder(self, mock_queue):
        """测试使用占位调用器总结（阶段 2-4）"""
        summarizer = Summarizer()
        
        # 阶段 2-4 使用占位实现，应该返回 None
        summary = await summarizer.summarize(mock_queue)
        
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_summarize_empty_queue(self):
        """测试总结空队列"""
        summarizer = Summarizer()
        queue = MessageQueue(group_id="group_123")
        
        summary = await summarizer.summarize(queue)
        
        assert summary is None
    
    @pytest.mark.asyncio
    async def test_summarize_with_custom_caller(self, mock_queue):
        """测试使用自定义调用器总结"""
        # 创建模拟调用器
        mock_caller = AsyncMock()
        mock_caller.call = AsyncMock(return_value="这是一个总结")
        
        summarizer = Summarizer(llm_caller=mock_caller)
        
        summary = await summarizer.summarize(mock_queue)
        
        assert summary == "这是一个总结"
        assert mock_caller.call.called
    
    def test_build_summary_prompt(self):
        """测试构建总结提示词"""
        summarizer = Summarizer()
        
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"}
        ]
        
        prompt = summarizer._build_summary_prompt(messages)
        
        assert "你好" in prompt
        assert "你好！" in prompt
        assert "总结" in prompt
