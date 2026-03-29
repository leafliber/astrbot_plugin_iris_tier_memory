"""测试 GetGroupProfileTool（占位符）"""

import pytest
from unittest.mock import Mock
from iris_memory.tools import GetGroupProfileTool


@pytest.fixture
def tool():
    """创建Tool实例"""
    return GetGroupProfileTool()


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
    assert tool.name == "get_group_profile"
    assert "画像" in tool.description


@pytest.mark.asyncio
async def test_placeholder_returns_message(tool, mock_context, monkeypatch):
    """测试占位符返回提示消息"""
    # 模拟platform adapter
    mock_adapter = Mock()
    mock_adapter.get_group_id = Mock(return_value="group_123")
    
    monkeypatch.setattr("iris_memory.tools.get_group_profile.get_adapter", Mock(return_value=mock_adapter))
    
    result = await tool.call(mock_context)
    
    # 验证返回占位符消息
    assert result.result is not None
    assert "开发中" in result.result or "阶段9" in result.result or "后续版本" in result.result


@pytest.mark.asyncio
async def test_custom_group_id(tool, mock_context, monkeypatch):
    """测试自定义群ID"""
    mock_adapter = Mock()
    mock_adapter.get_group_id = Mock(return_value="group_123")
    
    monkeypatch.setattr("iris_memory.tools.get_group_profile.get_adapter", Mock(return_value=mock_adapter))
    
    result = await tool.call(mock_context, group_id="custom_group_456")
    
    assert "custom_group_456" in result.result
