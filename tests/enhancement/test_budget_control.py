"""
测试 Token 预算控制器
"""

import pytest
from iris_memory.l2_memory.models import MemoryEntry, MemorySearchResult
from iris_memory.enhancement.budget_control import TokenBudgetController


def create_memory_result(content: str, memory_id: str = None) -> MemorySearchResult:
    """创建测试用的记忆检索结果"""
    entry = MemoryEntry(
        id=memory_id or f"mem_{hash(content)}",
        content=content,
        metadata={}
    )
    return MemorySearchResult(entry=entry, score=0.9, distance=0.1)


class TestTokenBudgetController:
    """Token 预算控制器测试"""
    
    def test_estimate_tokens_with_character_estimation(self):
        """测试字符估算"""
        controller = TokenBudgetController()
        
        # 测试中文文本
        text_zh = "你好世界"
        tokens_zh = controller.estimate_tokens(text_zh)
        assert tokens_zh > 0
        assert tokens_zh == len(text_zh) // 2 + 1
        
        # 测试英文文本
        text_en = "Hello World"
        tokens_en = controller.estimate_tokens(text_en)
        assert tokens_en > 0
        assert tokens_en == len(text_en) // 2 + 1
        
        # 测试空文本
        tokens_empty = controller.estimate_tokens("")
        assert tokens_empty == 0
    
    def test_trim_memories_basic(self):
        """测试基础裁剪功能"""
        controller = TokenBudgetController(max_tokens=100)
        
        memories = [
            create_memory_result("这是一条测试记忆，长度适中"),
            create_memory_result("这是另一条测试记忆，也比较适中"),
            create_memory_result("这是第三条测试记忆，同样适中"),
        ]
        
        trimmed, total_tokens = controller.trim_memories(memories)
        
        # 验证裁剪后的记忆数量
        assert len(trimmed) > 0
        assert len(trimmed) <= len(memories)
        
        # 验证总 Token 数在预算内
        assert total_tokens <= 100
    
    def test_trim_memories_with_budget_exceeded(self):
        """测试超出预算时的裁剪"""
        controller = TokenBudgetController(max_tokens=50)
        
        # 创建多条记忆，总 Token 数将超出预算
        memories = [
            create_memory_result("这是一条比较长的测试记忆，用于测试Token预算控制功能是否正常工作"),
            create_memory_result("这是另一条比较长的测试记忆，同样用于测试Token预算控制功能"),
            create_memory_result("这是第三条比较长的测试记忆，继续测试Token预算控制功能"),
        ]
        
        trimmed, total_tokens = controller.trim_memories(memories)
        
        # 验证裁剪后的记忆数量小于原始数量
        assert len(trimmed) < len(memories)
        
        # 验证总 Token 数在预算内
        assert total_tokens <= 50
    
    def test_trim_memories_single_memory_exceeds_budget(self):
        """测试单条记忆超出预算的情况"""
        controller = TokenBudgetController(max_tokens=10)
        
        # 创建一条超长的记忆
        long_content = "这是一条非常非常非常非常非常长的测试记忆，远远超出Token预算"
        memories = [create_memory_result(long_content)]
        
        trimmed, total_tokens = controller.trim_memories(memories)
        
        # 验证仍然保留第一条记忆（避免空结果）
        assert len(trimmed) == 1
        assert trimmed[0].entry.content == long_content
    
    def test_trim_memories_empty_list(self):
        """测试空记忆列表"""
        controller = TokenBudgetController()
        
        trimmed, total_tokens = controller.trim_memories([])
        
        assert len(trimmed) == 0
        assert total_tokens == 0
    
    def test_estimate_total_tokens(self):
        """测试估算总 Token 数"""
        controller = TokenBudgetController()
        
        memories = [
            create_memory_result("测试记忆一"),
            create_memory_result("测试记忆二"),
            create_memory_result("测试记忆三"),
        ]
        
        total = controller.estimate_total_tokens(memories)
        
        # 验证总 Token 数正确
        expected = sum(
            controller.estimate_tokens(m.entry.content)
            for m in memories
        )
        assert total == expected
    
    def test_can_fit(self):
        """测试预算检查"""
        controller = TokenBudgetController(max_tokens=100)
        
        memories = [
            create_memory_result("短记忆一"),
            create_memory_result("短记忆二"),
        ]
        
        # 验证记忆列表在预算内
        assert controller.can_fit(memories)
        
        # 验证带额外预留的检查
        assert controller.can_fit(memories, additional_tokens=50)
        assert not controller.can_fit(memories, additional_tokens=200)
    
    def test_trim_memories_preserve_order(self):
        """测试保持原始顺序"""
        controller = TokenBudgetController(max_tokens=200)
        
        memories = [
            create_memory_result("记忆A", "mem_a"),
            create_memory_result("记忆B", "mem_b"),
            create_memory_result("记忆C", "mem_c"),
        ]
        
        trimmed, _ = controller.trim_memories(memories, preserve_order=True)
        
        # 验证顺序保持不变
        assert [m.entry.id for m in trimmed] == ["mem_a", "mem_b", "mem_c"]
