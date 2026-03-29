"""测试 SaveMemoryTool"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from iris_memory.tools import SaveMemoryTool


@pytest.fixture
def tool():
    """创建Tool实例"""
    return SaveMemoryTool()


@pytest.fixture
def mock_context():
    """创建模拟上下文"""
    context = Mock()
    
    # 模拟event
    event = Mock()
    event.user_id = "test_user_123"
    
    # 模拟context.context
    inner_context = Mock()
    inner_context.event = event
    context.context = inner_context
    
    return context


@pytest.mark.asyncio
async def test_tool_initialization(tool):
    """测试Tool初始化"""
    assert tool.name == "save_memory"
    assert "记忆" in tool.description
    assert "content" in tool.parameters["properties"]


@pytest.mark.asyncio
async def test_save_memory_success(tool, mock_context, monkeypatch):
    """测试成功保存记忆"""
    # 模拟platform adapter
    mock_adapter = Mock()
    mock_adapter.get_user_id = Mock(return_value="user_123")
    mock_adapter.get_group_id = Mock(return_value="group_456")
    mock_adapter.get_user_name = Mock(return_value="测试用户")
    
    # 模拟config
    mock_config = Mock()
    mock_config.get = Mock(return_value=True)
    
    # 模拟L2 adapter
    mock_l2 = Mock()
    mock_l2._is_available = True
    mock_l2.add_memory = AsyncMock(return_value="mem_test123")
    
    # 模拟component manager
    mock_manager = Mock()
    mock_manager.get_component = Mock(return_value=mock_l2)
    
    # 应用monkeypatch
    monkeypatch.setattr("iris_memory.tools.save_memory.get_adapter", Mock(return_value=mock_adapter))
    monkeypatch.setattr("iris_memory.tools.save_memory.get_config", Mock(return_value=mock_config))
    monkeypatch.setattr("iris_memory.tools.save_memory.get_component_manager", Mock(return_value=mock_manager))
    
    # 执行Tool
    result = await tool.call(
        mock_context,
        content="测试记忆内容",
        confidence=0.9
    )
    
    # 验证结果
    assert result.result is not None
    assert "成功" in result.result or "已保存" in result.result


@pytest.mark.asyncio
async def test_save_memory_empty_content(tool, mock_context):
    """测试空内容"""
    result = await tool.call(mock_context, content="")
    assert "不能为空" in result.result


@pytest.mark.asyncio
async def test_save_memory_l2_unavailable(tool, mock_context, monkeypatch):
    """测试L2不可用"""
    # 模拟platform adapter
    mock_adapter = Mock()
    mock_adapter.get_user_id = Mock(return_value="user_123")
    mock_adapter.get_group_id = Mock(return_value="group_456")
    mock_adapter.get_user_name = Mock(return_value="测试用户")
    
    # 模拟config
    mock_config = Mock()
    mock_config.get = Mock(return_value=True)
    
    # 模拟不可用的L2
    mock_l2 = Mock()
    mock_l2._is_available = False
    
    mock_manager = Mock()
    mock_manager.get_component = Mock(return_value=mock_l2)
    
    # 应用monkeypatch
    monkeypatch.setattr("iris_memory.tools.save_memory.get_adapter", Mock(return_value=mock_adapter))
    monkeypatch.setattr("iris_memory.tools.save_memory.get_config", Mock(return_value=mock_config))
    monkeypatch.setattr("iris_memory.tools.save_memory.get_component_manager", Mock(return_value=mock_manager))
    
    result = await tool.call(mock_context, content="测试内容")
    assert "不可用" in result.result
