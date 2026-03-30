"""L3 知识图谱实体提取器测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import tempfile
import shutil

from iris_memory.l3_kg import EntityExtractor, GraphNode, GraphEdge
from iris_memory.config import init_config


class TestEntityExtractor:
    """EntityExtractor 测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def mock_llm_manager(self):
        """创建模拟 LLM 管理器"""
        manager = MagicMock()
        manager.generate = AsyncMock()
        manager.is_available = True
        return manager
    
    @pytest.fixture
    def extractor(self, mock_llm_manager, temp_dir):
        """创建提取器实例"""
        # 初始化配置
        from iris_memory.config import Config
        from astrbot.api import AstrBotConfig
        
        config_dict = {
            "l3_kg": {
                "enable": True,
                "enable_type_whitelist": True
            }
        }
        mock_config = AstrBotConfig(config_dict)
        init_config(mock_config, temp_dir)
        
        return EntityExtractor(mock_llm_manager)
    
    def test_build_extraction_prompt(self, extractor):
        """测试构建提取 prompt"""
        text = "Alice 和 Bob 讨论了 AI 技术"
        
        prompt = extractor._build_extraction_prompt(text)
        
        # 验证 prompt 包含必要内容
        assert "Alice 和 Bob 讨论了 AI 技术" in prompt
        assert "节点类型白名单" in prompt
        assert "关系类型白名单" in prompt
        assert "Person" in prompt  # 白名单中的类型
        assert "KNOWS" in prompt  # 白名单中的关系
    
    def test_build_extraction_prompt_without_whitelist(self, extractor):
        """测试不使用白名单的 prompt"""
        # 修改配置
        extractor.config._hidden_config.data["l3_kg.enable_type_whitelist"] = False
        
        text = "Alice 和 Bob 讨论了 AI 技术"
        prompt = extractor._build_extraction_prompt(text)
        
        # 验证不包含白名单提示
        assert "节点类型白名单" not in prompt
    
    @pytest.mark.asyncio
    async def test_parse_extraction_result_success(self, extractor):
        """测试解析成功的提取结果"""
        llm_response = """```json
{
  "nodes": [
    {
      "label": "Person",
      "name": "Alice",
      "content": "软件工程师",
      "confidence": 0.9
    },
    {
      "label": "Person",
      "name": "Bob",
      "content": "数据科学家",
      "confidence": 0.85
    }
  ],
  "edges": [
    {
      "source_name": "Alice",
      "target_name": "Bob",
      "relation_type": "KNOWS",
      "confidence": 0.8
    }
  ],
  "extraction_confidence": 0.85
}
```"""
        
        context = {
            "group_id": "group_123",
            "source_memory_id": "mem_456"
        }
        
        result = extractor._parse_extraction_result(llm_response, context)
        
        # 验证结果
        assert not result.is_empty()
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.extraction_confidence == 0.85
        
        # 验证节点
        alice_node = result.nodes[0]
        assert alice_node.label == "Person"
        assert alice_node.name == "Alice"
        assert alice_node.confidence == 0.9
        assert alice_node.group_id == "group_123"
        
        # 验证边
        edge = result.edges[0]
        assert edge.relation_type == "KNOWS"
        assert edge.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_parse_extraction_result_empty(self, extractor):
        """测试解析空的提取结果"""
        llm_response = """```json
{
  "nodes": [],
  "edges": [],
  "extraction_confidence": 0.5
}
```"""
        
        result = extractor._parse_extraction_result(llm_response, {})
        
        assert result.is_empty()
        assert len(result.nodes) == 0
        assert len(result.edges) == 0
    
    @pytest.mark.asyncio
    async def test_parse_extraction_result_invalid_json(self, extractor):
        """测试解析无效 JSON"""
        llm_response = "这不是 JSON 格式"
        
        result = extractor._parse_extraction_result(llm_response, {})
        
        # 应该返回空结果
        assert result.is_empty()
    
    @pytest.mark.asyncio
    async def test_extract_from_text_success(self, extractor, mock_llm_manager):
        """测试完整的提取流程"""
        # 模拟 LLM 响应
        mock_llm_manager.generate.return_value = """{
  "nodes": [
    {
      "label": "Person",
      "name": "Alice",
      "content": "软件工程师",
      "confidence": 0.9
    }
  ],
  "edges": [],
  "extraction_confidence": 0.9
}"""
        
        text = "Alice 是一名软件工程师，她喜欢编程"
        context = {"group_id": "group_123"}
        
        result = await extractor.extract_from_text(text, context)
        
        # 验证调用
        mock_llm_manager.generate.assert_called_once()
        
        # 验证结果
        assert not result.is_empty()
        assert len(result.nodes) == 1
        assert result.nodes[0].name == "Alice"
    
    @pytest.mark.asyncio
    async def test_extract_from_text_with_llm_error(self, extractor, mock_llm_manager):
        """测试 LLM 调用失败"""
        # 模拟 LLM 抛出异常
        mock_llm_manager.generate.side_effect = Exception("LLM 调用失败")
        
        text = "测试文本"
        result = await extractor.extract_from_text(text, {})
        
        # 应该返回空结果
        assert result.is_empty()
    
    @pytest.mark.asyncio
    async def test_extract_from_text_creates_valid_ids(self, extractor, mock_llm_manager):
        """测试提取结果生成有效 ID"""
        mock_llm_manager.generate.return_value = """{
  "nodes": [
    {
      "label": "Person",
      "name": "Alice",
      "content": "软件工程师",
      "confidence": 0.9
    }
  ],
  "edges": [],
  "extraction_confidence": 0.9
}"""
        
        result = await extractor.extract_from_text("测试", {})
        
        # 验证节点 ID 已生成
        assert len(result.nodes) == 1
        node = result.nodes[0]
        assert node.id != ""
        assert node.id.startswith("person_")
    
    @pytest.mark.asyncio
    async def test_extract_from_text_handles_dynamic_types(self, extractor, mock_llm_manager):
        """测试动态类型处理"""
        # 使用不在白名单中的类型
        mock_llm_manager.generate.return_value = """{
  "nodes": [
    {
      "label": "CustomType",
      "name": "CustomEntity",
      "content": "自定义实体",
      "confidence": 0.8
    }
  ],
  "edges": [
    {
      "source_name": "CustomEntity",
      "target_name": "CustomEntity",
      "relation_type": "CUSTOM_RELATION",
      "confidence": 0.7
    }
  ],
  "extraction_confidence": 0.75
}"""
        
        result = await extractor.extract_from_text("测试", {})
        
        # 验证动态类型被接受
        assert len(result.nodes) == 1
        assert result.nodes[0].label == "CustomType"
        
        assert len(result.edges) == 1
        assert result.edges[0].relation_type == "CUSTOM_RELATION"
