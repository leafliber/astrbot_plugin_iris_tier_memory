"""L1 数据模型测试"""

import pytest
from datetime import datetime
from iris_memory.l1_buffer.models import ContextMessage, MessageQueue


class TestContextMessage:
    """ContextMessage 测试"""
    
    def test_create_message(self):
        """测试创建消息"""
        msg = ContextMessage(
            role="user",
            content="你好",
            timestamp=datetime.now(),
            token_count=2,
            source="group_123"
        )
        
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.token_count == 2
        assert msg.source == "group_123"
        assert msg.metadata == {}
    
    def test_message_with_metadata(self):
        """测试带元数据的消息"""
        metadata = {"user_id": "user_456", "nickname": "测试用户"}
        msg = ContextMessage(
            role="user",
            content="测试",
            timestamp=datetime.now(),
            token_count=1,
            source="group_123",
            metadata=metadata
        )
        
        assert msg.metadata == metadata
    
    def test_to_dict(self):
        """测试转换为字典"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        msg = ContextMessage(
            role="user",
            content="测试",
            timestamp=timestamp,
            token_count=1,
            source="group_123"
        )
        
        data = msg.to_dict()
        
        assert data["role"] == "user"
        assert data["content"] == "测试"
        assert data["timestamp"] == "2024-01-01T12:00:00"
        assert data["token_count"] == 1
        assert data["source"] == "group_123"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "role": "assistant",
            "content": "回复",
            "timestamp": "2024-01-01T12:00:00",
            "token_count": 3,
            "source": "assistant",
            "metadata": {"test": "value"}
        }
        
        msg = ContextMessage.from_dict(data)
        
        assert msg.role == "assistant"
        assert msg.content == "回复"
        assert msg.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert msg.token_count == 3
        assert msg.metadata == {"test": "value"}


class TestMessageQueue:
    """MessageQueue 测试"""
    
    def test_create_queue(self):
        """测试创建队列"""
        queue = MessageQueue(group_id="group_123")
        
        assert queue.group_id == "group_123"
        assert len(queue) == 0
        assert queue.total_tokens == 0
    
    def test_add_message(self):
        """测试添加消息"""
        queue = MessageQueue(group_id="group_123")
        msg = ContextMessage(
            role="user",
            content="测试",
            timestamp=datetime.now(),
            token_count=5,
            source="user_456"
        )
        
        queue.add_message(msg)
        
        assert len(queue) == 1
        assert queue.total_tokens == 5
    
    def test_add_multiple_messages(self):
        """测试添加多条消息"""
        queue = MessageQueue(group_id="group_123")
        
        for i in range(3):
            msg = ContextMessage(
                role="user",
                content=f"消息{i}",
                timestamp=datetime.now(),
                token_count=2,
                source="user_456"
            )
            queue.add_message(msg)
        
        assert len(queue) == 3
        assert queue.total_tokens == 6
    
    def test_remove_oldest(self):
        """测试移除最旧消息"""
        queue = MessageQueue(group_id="group_123")
        
        msg1 = ContextMessage(
            role="user",
            content="消息1",
            timestamp=datetime.now(),
            token_count=5,
            source="user_456"
        )
        msg2 = ContextMessage(
            role="assistant",
            content="消息2",
            timestamp=datetime.now(),
            token_count=3,
            source="assistant"
        )
        
        queue.add_message(msg1)
        queue.add_message(msg2)
        
        removed = queue.remove_oldest()
        
        assert removed.content == "消息1"
        assert len(queue) == 1
        assert queue.total_tokens == 3
    
    def test_remove_oldest_empty_queue(self):
        """测试空队列移除"""
        queue = MessageQueue(group_id="group_123")
        
        removed = queue.remove_oldest()
        
        assert removed is None
    
    def test_clear(self):
        """测试清空队列"""
        queue = MessageQueue(group_id="group_123")
        
        for i in range(5):
            msg = ContextMessage(
                role="user",
                content=f"消息{i}",
                timestamp=datetime.now(),
                token_count=1,
                source="user_456"
            )
            queue.add_message(msg)
        
        queue.clear()
        
        assert len(queue) == 0
        assert queue.total_tokens == 0
    
    def test_is_empty(self):
        """测试队列判空"""
        queue = MessageQueue(group_id="group_123")
        
        assert queue.is_empty()
        
        msg = ContextMessage(
            role="user",
            content="测试",
            timestamp=datetime.now(),
            token_count=1,
            source="user_456"
        )
        queue.add_message(msg)
        
        assert not queue.is_empty()
    
    def test_to_message_list(self):
        """测试转换为消息列表"""
        queue = MessageQueue(group_id="group_123")
        
        msg1 = ContextMessage(
            role="user",
            content="你好",
            timestamp=datetime.now(),
            token_count=2,
            source="user_456"
        )
        msg2 = ContextMessage(
            role="assistant",
            content="你好！",
            timestamp=datetime.now(),
            token_count=3,
            source="assistant"
        )
        
        queue.add_message(msg1)
        queue.add_message(msg2)
        
        message_list = queue.to_message_list()
        
        assert len(message_list) == 2
        assert message_list[0] == {"role": "user", "content": "你好"}
        assert message_list[1] == {"role": "assistant", "content": "你好！"}
