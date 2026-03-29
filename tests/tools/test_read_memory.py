"""测试 ReadMemoryTool"""

import pytest
from unittest.mock import Mock, AsyncMock
from iris_memory.tools import ReadMemoryTool
from iris_memory.l2_memory import MemoryEntry, MemorySearchResult


@pytest.fixture
def tool():
    """创建Tool实例"""
    return ReadMemoryTool()


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
    assert tool.name == "read_memory"
    assert "检索" in tool.description or "读取" in tool.description
    assert "query" in tool.parameters["properties"]


@pytest.mark.asyncio
async def test_read_memory_success(tool, mock_context, monkeypatch):
    """测试成功检索记忆"""
    # 创建模拟搜索结果
    mock_entry = MemoryEntry(
        id="mem_test123",
        content="用户喜欢吃苹果",
        metadata={"confidence": 0.9}
    )
    mock_result = MemorySearchResult(entry=mock_entry, score=0.95, distance=0.05)
    
    # 模拟platform adapter
    mock_adapter = Mock()
    mock_adapter.get_user_id = Mock(return_value="user_123")
    mock_adapter.get_group_id = Mock(return_value="group_456")
    
    # 模拟config
    mock_config = Mock()
    mock_config.get = Mock(return_value=True)
    
    # 模拟L2 adapter
    mock_l2 = Mock()
    mock_l2._is_available = True
    mock_l2.search = AsyncMock(return_value=[mock_result])
    
    # 模拟manager
    mock_manager = Mock()
    mock_manager.get_component = Mock(return_value=mock_l2)
    
    # 应用monkeypatch
    monkeypatch.setattr("iris_memory.tools.read_memory.get_adapter", Mock(return_value=mock_adapter))
    monkeypatch.setattr("iris_memory.tools.read_memory.get_config", Mock(return_value=mock_config))
    monkeypatch.setattr("iris_memory.tools.read_memory.get_component_manager", Mock(return_value=mock_manager))
    
    result = await tool.call(mock_context, query="用户偏好")
    
    assert result.result is not None
    assert "找到" in result.result or "记忆" in result.result


@pytest.mark.asyncio
async def test_read_memory_empty_query(tool, mock_context):
    """测试空查询"""
    result = await tool.call(mock_context, query="")
    assert "不能为空" in result.result


@pytest.mark.asyncio
async def test_read_memory_no_results(tool, mock_context, monkeypatch):
    """测试无结果"""
    # 模拟platform adapter
    mock_adapter = Mock()
    mock_adapter.get_user_id = Mock(return_value="user_123")
    mock_adapter.get_group_id = Mock(return_value="group_456")
    
    # 模拟config
    mock_config = Mock()
    mock_config.get = Mock(return_value=True)
    
    # 模拟L2返回空结果
    mock_l2 = Mock()
    mock_l2._is_available = True
    mock_l2.search = AsyncMock(return_value=[])
    
    mock_manager = Mock()
    mock_manager.get_component = Mock(return_value=mock_l2)
    
    monkeypatch.setattr("iris_memory.tools.read_memory.get_adapter", Mock(return_value=mock_adapter))
    monkeypatch.setattr("iris_memory.tools.read_memory.get_config", Mock(return_value=mock_config))
    monkeypatch.setattr("iris_memory.tools.read_memory.get_component_manager", Mock(return_value=mock_manager))
    
    result = await tool.call(mock_context, query="不存在的记忆")
    assert "未找到" in result.result
