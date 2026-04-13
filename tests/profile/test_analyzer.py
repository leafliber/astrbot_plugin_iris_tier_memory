"""画像分析器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from iris_memory.profile.analyzer import ProfileAnalyzer


class TestProfileAnalyzer:
    """画像分析器测试"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """创建模拟的 LLMManager"""
        manager = MagicMock()
        manager.generate = AsyncMock()
        return manager
    
    @pytest.fixture
    def analyzer(self, mock_llm_manager):
        """创建 ProfileAnalyzer 实例"""
        return ProfileAnalyzer(mock_llm_manager)
    
    @pytest.mark.asyncio
    async def test_analyze_group_profile(self, analyzer, mock_llm_manager):
        """测试分析群聊画像"""
        llm_response = json.dumps({
            "interests": ["技术", "AI"],
            "atmosphere_tags": ["轻松", "技术范"]
        }, ensure_ascii=False)
        mock_llm_manager.generate.return_value = llm_response
        
        messages = ["今天讨论了AI技术", "yyds!", "这个方案绝了"]
        current_profile = {}
        
        result = await analyzer.analyze_group_profile(messages, current_profile)
        
        assert result["interests"] == ["技术", "AI"]
        assert result["atmosphere_tags"] == ["轻松", "技术范"]
        mock_llm_manager.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_user_profile(self, analyzer, mock_llm_manager):
        """测试分析用户画像"""
        llm_response = json.dumps({
            "personality_tags": ["外向", "幽默"],
            "interests": ["编程", "游戏"],
            "language_style": "简洁"
        }, ensure_ascii=False)
        mock_llm_manager.generate.return_value = llm_response
        
        messages = ["哈哈哈今天天气真好", "最近在学Python"]
        current_profile = {}
        
        result = await analyzer.analyze_user_profile(messages, current_profile)
        
        assert result["personality_tags"] == ["外向", "幽默"]
        assert result["interests"] == ["编程", "游戏"]
        assert result["language_style"] == "简洁"
        mock_llm_manager.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_with_llm_failure(self, analyzer, mock_llm_manager):
        """测试 LLM 调用失败"""
        mock_llm_manager.generate.side_effect = Exception("LLM 调用失败")
        
        messages = ["测试消息"]
        current_profile = {}
        
        result = await analyzer.analyze_group_profile(messages, current_profile)
        
        # 失败时返回空字典
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_analyze_with_invalid_json(self, analyzer, mock_llm_manager):
        """测试 LLM 返回无效 JSON"""
        mock_llm_manager.generate.return_value = "这不是 JSON"
        
        messages = ["测试消息"]
        current_profile = {}
        
        result = await analyzer.analyze_group_profile(messages, current_profile)
        
        # 无效 JSON 时返回空字典
        assert result == {}
    
    def test_build_group_analysis_prompt(self, analyzer):
        """测试构建群聊分析 prompt"""
        messages = ["消息1", "消息2", "消息3"]
        current_profile = {"interests": ["技术"]}
        
        prompt = analyzer._build_group_analysis_prompt(messages, current_profile)
        
        assert "群聊画像特征" in prompt
        assert "消息1" in prompt
        assert "消息2" in prompt
        assert "技术" in prompt
    
    def test_build_user_analysis_prompt(self, analyzer):
        """测试构建用户分析 prompt"""
        messages = ["用户消息1", "用户消息2"]
        current_profile = {"personality_tags": ["外向"]}
        
        prompt = analyzer._build_user_analysis_prompt(messages, current_profile)
        
        assert "用户画像特征" in prompt
        assert "用户消息1" in prompt
        assert "用户消息2" in prompt
        assert "外向" in prompt
