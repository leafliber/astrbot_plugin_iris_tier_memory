"""测试 CorrectMemoryTool"""

import pytest
from unittest.mock import Mock, AsyncMock
from iris_memory.tools import CorrectMemoryTool
from iris_memory.l2_memory import MemoryEntry, MemorySearchResult


@pytest.fixture
def tool():
    """创建Tool实例"""
    return CorrectMemoryTool()


@pytest.fixture
def mock_context():
    """创建模拟上下文"""
    context = Mock()
    event = Mock()
    inner_context = Mock()
    inner_context.event = event
    context.context = inner_context
    return context


@pytest.mark.asyncio
async def test_tool_initialization(tool):
    """测试Tool初始化"""
    assert tool.name == "correct_memory"
    assert "修正" in tool.description or "纠正" in tool.description
    assert "memory_id" in tool.parameters["properties"]


@pytest.mark.asyncio
async def test_correct_memory_missing_params(tool, mock_context):
    """测试缺少参数"""
    result = await tool.call(mock_context, memory_id="mem_123")
    assert "参数不完整" in result.result


@pytest.mark.asyncio
async def test_correct_memory_l2_unavailable(tool, mock_context, monkeypatch):
    """测试L2不可用"""
    mock_adapter = Mock()
    mock_adapter.get_user_id = Mock(return_value="user_123")
    mock_adapter.get_group_id = Mock(return_value="group_456")
    
    # L2不可用
    mock_l2 = Mock()
    mock_l2._is_available = False
    
    mock_manager = Mock()
    mock_manager.get_component = Mock(return_value=mock_l2)
    
    monkeypatch.setattr("iris_memory.tools.correct_memory.get_adapter", Mock(return_value=mock_adapter))
    monkeypatch.setattr("iris_memory.tools.correct_memory.get_component_manager", Mock(return_value=mock_manager))
    
    result = await tool.call(
        mock_context,
        memory_id="mem_123",
        correction="修正内容",
        reason="修正原因"
    )
    
    assert "不可用" in result.result
