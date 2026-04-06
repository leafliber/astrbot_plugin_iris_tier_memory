"""L1 缓冲组件测试"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from iris_memory.l1_buffer import L1Buffer, ContextMessage
from iris_memory.config import init_config


@pytest.fixture
def mock_config(tmp_path: Path):
    """模拟配置"""
    astrbot_config = Mock()
    astrbot_config.__getitem__ = Mock(return_value={
        "enable": True,
        "summary_provider": "",
        "inject_queue_length": 20,
        "max_queue_tokens": 4000,
        "max_single_message_tokens": 500
    })
    astrbot_config.__contains__ = Mock(return_value=True)
    
    return init_config(astrbot_config, tmp_path)


class TestL1Buffer:
    """L1 缓冲组件测试"""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_config):
        """测试初始化成功"""
        buffer = L1Buffer()
        
        await buffer.initialize()
        
        assert buffer.is_available
        assert buffer.name == "l1_buffer"
    
    @pytest.mark.asyncio
    async def test_initialize_disabled(self, mock_config):
        """测试禁用状态初始化"""
        with patch('iris_memory.l1_buffer.buffer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.enable": False
            }.get(key, None))
            
            buffer = L1Buffer()
            await buffer.initialize()
            
            assert not buffer.is_available
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_config):
        """测试关闭"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        # 添加一些消息
        await buffer.add_message("group_123", "user", "测试", "user_456")
        
        await buffer.shutdown()
        
        assert not buffer.is_available
        assert len(buffer._queues) == 0
    
    @pytest.mark.asyncio
    async def test_add_message_success(self, mock_config):
        """测试添加消息成功"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        success = await buffer.add_message(
            group_id="group_123",
            role="user",
            content="你好",
            source="user_456"
        )
        
        assert success
        
        context = buffer.get_context("group_123")
        assert len(context) == 1
        assert context[0].content == "你好"
    
    @pytest.mark.asyncio
    async def test_add_message_too_large(self, mock_config):
        """测试添加超大消息"""
        with patch('iris_memory.l1_buffer.buffer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.enable": True,
                "l1_buffer.max_single_message_tokens": 10
            }.get(key, None))
            
            buffer = L1Buffer()
            await buffer.initialize()
            
            # 创建一个超过限制的消息
            large_content = "这是一条很长的消息" * 100
            
            success = await buffer.add_message(
                group_id="group_123",
                role="user",
                content=large_content,
                source="user_456"
            )
            
            assert not success
            
            context = buffer.get_context("group_123")
            assert len(context) == 0
    
    @pytest.mark.asyncio
    async def test_add_message_disabled(self, mock_config):
        """测试禁用时添加消息"""
        with patch('iris_memory.l1_buffer.buffer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.enable": False
            }.get(key, None))
            
            buffer = L1Buffer()
            await buffer.initialize()
            
            success = await buffer.add_message(
                group_id="group_123",
                role="user",
                content="测试",
                source="user_456"
            )
            
            assert not success
    
    @pytest.mark.asyncio
    async def test_get_context_with_limit(self, mock_config):
        """测试获取有限制的上下文"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        # 添加 10 条消息
        for i in range(10):
            await buffer.add_message(
                group_id="group_123",
                role="user",
                content=f"消息{i}",
                source="user_456"
            )
        
        # 获取最近 5 条
        context = buffer.get_context("group_123", max_length=5)
        
        assert len(context) == 5
        assert context[0].content == "消息5"
        assert context[4].content == "消息9"
    
    @pytest.mark.asyncio
    async def test_clear_context(self, mock_config):
        """测试清空指定队列"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        # 添加消息
        await buffer.add_message("group_123", "user", "测试", "user_456")
        
        buffer.clear_context("group_123")
        
        context = buffer.get_context("group_123")
        assert len(context) == 0
    
    @pytest.mark.asyncio
    async def test_clear_all(self, mock_config):
        """测试清空所有队列"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        # 添加消息到多个队列
        await buffer.add_message("group_123", "user", "测试1", "user_456")
        await buffer.add_message("group_456", "user", "测试2", "user_789")
        
        buffer.clear_all()
        
        assert len(buffer._queues) == 0
    
    @pytest.mark.asyncio
    async def test_group_isolation_always_enabled(self, mock_config):
        """测试 L1 缓冲始终按群隔离
        
        L1 不受 enable_group_memory_isolation 配置影响，始终分群存储。
        该配置仅控制 L2/L3 的查询是否带群 ID 条件。
        """
        with patch('iris_memory.l1_buffer.buffer.get_config') as mock_get_config:
            mock_get_config.return_value.get = Mock(side_effect=lambda key: {
                "l1_buffer.enable": True,
            }.get(key, None))
            
            buffer = L1Buffer()
            await buffer.initialize()
            
            await buffer.add_message("group_123", "user", "测试1", "user_456")
            await buffer.add_message("group_456", "user", "测试2", "user_789")
            
            assert len(buffer._queues) == 2
            
            context1 = buffer.get_context("group_123")
            context2 = buffer.get_context("group_456")
            
            assert len(context1) == 1
            assert len(context2) == 1
    
    @pytest.mark.asyncio
    async def test_get_queue_stats(self, mock_config):
        """测试获取队列统计"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        # 添加消息
        await buffer.add_message("group_123", "user", "测试", "user_456")
        
        stats = buffer.get_queue_stats("group_123")
        
        assert stats is not None
        assert stats["message_count"] == 1
        assert stats["total_tokens"] > 0
    
    @pytest.mark.asyncio
    async def test_get_queue_stats_nonexistent(self, mock_config):
        """测试获取不存在的队列统计"""
        buffer = L1Buffer()
        await buffer.initialize()
        
        stats = buffer.get_queue_stats("nonexistent_group")
        
        assert stats is None


class TestParseSummaryItems:
    """测试分条总结解析"""
    
    def test_parse_with_dash_prefix(self):
        """测试解析带 "- " 前缀的条目"""
        buffer = L1Buffer()
        
        summary = """- 用户提到喜欢吃苹果
- 用户询问了项目的配置方法
- 用户表示今天工作压力很大"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 3
        assert items[0] == "用户提到喜欢吃苹果"
        assert items[1] == "用户询问了项目的配置方法"
        assert items[2] == "用户表示今天工作压力很大"
    
    def test_parse_with_numbered_prefix(self):
        """测试解析带数字前缀的条目"""
        buffer = L1Buffer()
        
        summary = """1. 用户提到喜欢吃苹果
2. 用户询问了项目的配置方法
3. 用户表示今天工作压力很大"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 3
        assert items[0] == "用户提到喜欢吃苹果"
        assert items[1] == "用户询问了项目的配置方法"
        assert items[2] == "用户表示今天工作压力很大"
    
    def test_parse_with_bullet_prefix(self):
        """测试解析带 "• " 前缀的条目"""
        buffer = L1Buffer()
        
        summary = """• 用户提到喜欢吃苹果
• 用户询问了项目的配置方法"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 2
        assert items[0] == "用户提到喜欢吃苹果"
        assert items[1] == "用户询问了项目的配置方法"
    
    def test_parse_mixed_format(self):
        """测试解析混合格式的条目"""
        buffer = L1Buffer()
        
        summary = """- 用户提到喜欢吃苹果
1. 用户询问了项目的配置方法
• 用户表示今天工作压力很大"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 3
    
    def test_parse_empty_lines_ignored(self):
        """测试空行被忽略"""
        buffer = L1Buffer()
        
        summary = """- 用户提到喜欢吃苹果

- 用户询问了项目的配置方法

"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 2
    
    def test_parse_short_items_filtered(self):
        """测试短条目被过滤"""
        buffer = L1Buffer()
        
        summary = """- 用户提到喜欢吃苹果
- 短
- 用户询问了项目的配置方法
- abc
- 用户表示今天工作压力很大"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 3
        assert "短" not in items
        assert "abc" not in items
    
    def test_parse_min_length_parameter(self):
        """测试最小长度参数"""
        buffer = L1Buffer()
        
        summary = """- 用户提到喜欢吃苹果
- 短条目
- 用户询问了项目的配置方法"""
        
        items = buffer._parse_summary_items(summary, min_length=10)
        
        assert len(items) == 2
        assert "短条目" not in items
    
    def test_parse_plain_lines(self):
        """测试解析无前缀的普通行"""
        buffer = L1Buffer()
        
        summary = """用户提到喜欢吃苹果
用户询问了项目的配置方法
用户表示今天工作压力很大"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 3
    
    def test_parse_empty_summary(self):
        """测试空总结"""
        buffer = L1Buffer()
        
        items = buffer._parse_summary_items("")
        
        assert len(items) == 0
    
    def test_parse_whitespace_only(self):
        """测试仅包含空白字符的总结"""
        buffer = L1Buffer()
        
        summary = """   
   
"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 0
    
    def test_parse_chinese_numbered_prefix(self):
        """测试中文数字前缀"""
        buffer = L1Buffer()
        
        summary = """1、用户提到喜欢吃苹果
2、用户询问了项目的配置方法"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 2
        assert items[0] == "用户提到喜欢吃苹果"
        assert items[1] == "用户询问了项目的配置方法"
    
    def test_parse_parenthesis_prefix(self):
        """测试括号前缀"""
        buffer = L1Buffer()
        
        summary = """1) 用户提到喜欢吃苹果
2) 用户询问了项目的配置方法"""
        
        items = buffer._parse_summary_items(summary)
        
        assert len(items) == 2
        assert items[0] == "用户提到喜欢吃苹果"
        assert items[1] == "用户询问了项目的配置方法"
