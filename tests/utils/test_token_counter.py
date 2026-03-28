"""Token 计数工具测试"""

import pytest
from iris_memory.utils.token_counter import count_tokens, get_encoder, count_messages_tokens


class TestTokenCounter:
    """Token 计数工具测试"""
    
    def test_count_tokens_english(self):
        """测试英文文本计数"""
        # "Hello, world!" 通常为 4 tokens
        count = count_tokens("Hello, world!")
        assert count == 4
    
    def test_count_tokens_chinese(self):
        """测试中文文本计数"""
        # "你好，世界！" 通常为 9 tokens
        count = count_tokens("你好，世界！")
        # 中文 token 数可能因编码器不同而略有差异
        assert count > 0
    
    def test_count_tokens_empty_string(self):
        """测试空字符串"""
        count = count_tokens("")
        assert count == 0
    
    def test_count_tokens_long_text(self):
        """测试长文本"""
        long_text = "This is a longer piece of text. " * 100
        count = count_tokens(long_text)
        assert count > 100
    
    def test_get_encoder_caching(self):
        """测试编码器缓存"""
        # 获取两次相同的编码器
        encoder1 = get_encoder("cl100k_base")
        encoder2 = get_encoder("cl100k_base")
        
        # 应该是同一个实例
        assert encoder1 is encoder2
    
    def test_count_messages_tokens_empty(self):
        """测试空消息列表"""
        count = count_messages_tokens([])
        assert count == 0
    
    def test_count_messages_tokens_single(self):
        """测试单条消息"""
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        count = count_messages_tokens(messages)
        assert count > 0
    
    def test_count_messages_tokens_multiple(self):
        """测试多条消息"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        count = count_messages_tokens(messages)
        assert count > 0
    
    def test_count_messages_tokens_with_format_overhead(self):
        """测试消息格式开销"""
        messages = [
            {"role": "user", "content": "test"}
        ]
        count = count_messages_tokens(messages)
        
        # 格式开销应该包含在内（至少 4 tokens）
        # 实际内容 "test" 约为 1 token
        assert count > 1
