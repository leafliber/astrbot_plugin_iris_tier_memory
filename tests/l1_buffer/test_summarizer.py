"""总结器测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from iris_memory.l1_buffer import Summarizer, MessageQueue, ContextMessage


@pytest.fixture
def mock_llm_manager():
    """创建模拟 LLM 管理器"""
    manager = AsyncMock()
    manager.generate = AsyncMock(return_value="这是一个总结")
    return manager


@pytest.fixture
def mock_messages():
    """创建模拟消息列表"""
    messages = []
    for i in range(5):
        msg = ContextMessage(
            role="user" if i % 2 == 0 else "assistant",
            content=f"消息{i}",
            timestamp=datetime.now(),
            token_count=10,
            source="user_456"
        )
        messages.append(msg)
    return messages


@pytest.fixture
def mock_queue(mock_messages):
    """创建模拟队列"""
    queue = MessageQueue(group_id="group_123")
    for msg in mock_messages:
        queue.add_message(msg)
    return queue


class TestSummarizer:
    """总结器测试"""
    
    def test_create_summarizer(self, mock_llm_manager):
        """测试创建总结器"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        assert summarizer.llm_manager == mock_llm_manager
        assert summarizer.provider == ""
    
    def test_create_summarizer_with_provider(self, mock_llm_manager):
        """测试使用自定义 Provider 创建"""
        summarizer = Summarizer(
            llm_manager=mock_llm_manager,
            provider="gpt-4o-mini"
        )
        
        assert summarizer.provider == "gpt-4o-mini"
    
    def test_should_summarize_by_length(self, mock_queue):
        """测试按消息数量触发总结"""
        with patch('iris_memory.l1_buffer.summarizer.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.get = Mock(side_effect=lambda key: {
                "l1_buffer.inject_queue_length": 3,
                "l1_buffer.max_queue_tokens": 10000
            }.get(key))
            mock_get_config.return_value = mock_config
            
            summarizer = Summarizer(llm_manager=Mock())
            
            assert summarizer.should_summarize(mock_queue)
    
    def test_should_summarize_by_tokens(self, mock_queue):
        """测试按 Token 数触发总结"""
        with patch('iris_memory.l1_buffer.summarizer.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.get = Mock(side_effect=lambda key: {
                "l1_buffer.inject_queue_length": 100,
                "l1_buffer.max_queue_tokens": 40
            }.get(key))
            mock_get_config.return_value = mock_config
            
            summarizer = Summarizer(llm_manager=Mock())
            
            assert summarizer.should_summarize(mock_queue)
    
    def test_should_not_summarize(self, mock_queue):
        """测试不触发总结"""
        with patch('iris_memory.l1_buffer.summarizer.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.get = Mock(side_effect=lambda key: {
                "l1_buffer.inject_queue_length": 100,
                "l1_buffer.max_queue_tokens": 10000
            }.get(key))
            mock_get_config.return_value = mock_config
            
            summarizer = Summarizer(llm_manager=Mock())
            
            assert not summarizer.should_summarize(mock_queue)
    
    @pytest.mark.asyncio
    async def test_summarize_messages(self, mock_llm_manager, mock_messages):
        """测试总结消息列表"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        summary = await summarizer.summarize(mock_messages)
        
        assert summary == "这是一个总结"
        assert mock_llm_manager.generate.called
    
    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self, mock_llm_manager):
        """测试总结空消息列表"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        summary = await summarizer.summarize([])
        
        assert summary is None
    
    def test_build_summary_prompt(self, mock_llm_manager):
        """测试构建总结提示词"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        messages = [
            ContextMessage(
                role="user",
                content="你好",
                timestamp=datetime.now(),
                token_count=2,
                source="user_001",
                metadata={"user_name": "张三"}
            ),
            ContextMessage(
                role="assistant",
                content="你好！",
                timestamp=datetime.now(),
                token_count=3,
                source="bot"
            )
        ]
        
        prompt = summarizer._build_summary_prompt(messages)
        
        assert "[张三]: 你好" in prompt
        assert "[助手]: 你好！" in prompt
        assert "提取记忆信息" in prompt
        assert "memories" in prompt

    def test_build_summary_prompt_format(self, mock_llm_manager):
        """测试总结提示词包含提取格式要求"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        messages = [
            ContextMessage(
                role="user",
                content="我喜欢吃苹果",
                timestamp=datetime.now(),
                token_count=5,
                source="user_001",
                metadata={"user_name": "张三"}
            ),
            ContextMessage(
                role="assistant",
                content="好的，我记住了",
                timestamp=datetime.now(),
                token_count=5,
                source="bot"
            )
        ]
        
        prompt = summarizer._build_summary_prompt(messages)
        
        assert "信息价值" in prompt
        assert "独立完整" in prompt
        assert "非即时性" in prompt
        assert "JSON" in prompt
    
    def test_build_summary_prompt_with_user_names(self, mock_llm_manager):
        """测试总结提示词包含用户名"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        messages = [
            ContextMessage(
                role="user",
                content="我喜欢吃苹果",
                timestamp=datetime.now(),
                token_count=5,
                source="user_001",
                metadata={"user_name": "张三"}
            ),
            ContextMessage(
                role="user",
                content="我喜欢编程",
                timestamp=datetime.now(),
                token_count=5,
                source="user_002",
                metadata={"user_name": "李四"}
            )
        ]
        
        prompt = summarizer._build_summary_prompt(messages)
        
        assert "[张三]: 我喜欢吃苹果" in prompt
        assert "[李四]: 我喜欢编程" in prompt
    
    def test_build_summary_prompt_without_user_name(self, mock_llm_manager):
        """测试没有用户名时显示默认标签"""
        summarizer = Summarizer(llm_manager=mock_llm_manager)
        
        messages = [
            ContextMessage(
                role="user",
                content="你好",
                timestamp=datetime.now(),
                token_count=2,
                source="user_001"
            )
        ]
        
        prompt = summarizer._build_summary_prompt(messages)
        
        assert "[用户]: 你好" in prompt


class TestMessageQueueSplit:
    """消息队列分割测试"""
    
    def test_split_basic(self, mock_queue):
        """测试基本分割"""
        to_summarize, to_retain = mock_queue.split_for_summary(retain_count=3)
        
        assert len(to_summarize) == 2
        assert len(to_retain) == 3
    
    def test_split_no_need(self):
        """测试无需分割"""
        queue = MessageQueue(group_id="test")
        for i in range(3):
            queue.add_message(ContextMessage(
                role="user",
                content=f"消息{i}",
                timestamp=datetime.now(),
                token_count=10,
                source="user"
            ))
        
        to_summarize, to_retain = queue.split_for_summary(retain_count=5)
        
        assert len(to_summarize) == 0
        assert len(to_retain) == 3
    
    def test_split_with_token_limit(self):
        """测试带 Token 限制的分割"""
        queue = MessageQueue(group_id="test")
        for i in range(10):
            queue.add_message(ContextMessage(
                role="user",
                content=f"消息{i}",
                timestamp=datetime.now(),
                token_count=100,
                source="user"
            ))
        
        to_summarize, to_retain = queue.split_for_summary(
            retain_count=5,
            max_retain_tokens=200
        )
        
        retain_tokens = sum(msg.token_count for msg in to_retain)
        assert retain_tokens <= 200
        assert len(to_retain) >= 1
    
    def test_remove_messages(self, mock_queue):
        """测试移除消息"""
        messages = list(mock_queue.messages)
        to_remove = messages[:2]
        
        mock_queue.remove_messages(to_remove)
        
        assert len(mock_queue) == 3
        assert mock_queue.total_tokens == 30
