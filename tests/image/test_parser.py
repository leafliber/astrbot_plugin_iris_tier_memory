"""图片解析器测试"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from iris_memory.image import ImageParser, ImageInfo, ParseResult


class TestImageParser:
    """ImageParser 测试"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """模拟 LLM Manager"""
        manager = Mock()
        manager.generate_with_images = AsyncMock(return_value="这是一张风景图片，显示蓝天白云")
        return manager
    
    @pytest.fixture
    def parser(self, mock_llm_manager):
        """创建解析器实例"""
        return ImageParser(mock_llm_manager, provider="test_provider")
    
    @pytest.mark.asyncio
    async def test_parse_with_url(self, parser, mock_llm_manager):
        """测试使用 URL 解析图片"""
        image_info = ImageInfo(
            url="https://example.com/image.jpg",
            format="jpg"
        )
        
        result = await parser.parse(image_info)
        
        assert result.success
        assert result.content == "这是一张风景图片，显示蓝天白云"
        assert result.image_info == image_info
        
        # 验证调用参数
        mock_llm_manager.generate_with_images.assert_called_once()
        call_args = mock_llm_manager.generate_with_images.call_args
        assert call_args[1]["image_urls"] == ["https://example.com/image.jpg"]
        assert call_args[1]["module"] == "image_parsing"
        assert call_args[1]["provider_id"] == "test_provider"
    
    @pytest.mark.asyncio
    async def test_parse_with_file_path(self, parser):
        """测试使用文件路径解析图片（暂不支持）"""
        image_info = ImageInfo(
            file_path="/path/to/image.jpg",
            format="jpg"
        )
        
        result = await parser.parse(image_info)
        
        assert not result.success
        assert "本地图片暂不支持" in result.error_message
    
    @pytest.mark.asyncio
    async def test_parse_with_invalid_info(self, parser):
        """测试使用无效信息解析"""
        image_info = ImageInfo()
        
        result = await parser.parse(image_info)
        
        assert not result.success
        assert "图片信息无效" in result.error_message
    
    @pytest.mark.asyncio
    async def test_parse_with_llm_error(self, parser, mock_llm_manager):
        """测试 LLM 调用失败"""
        mock_llm_manager.generate_with_images.side_effect = Exception("网络错误")
        
        image_info = ImageInfo(url="https://example.com/image.jpg")
        result = await parser.parse(image_info)
        
        assert not result.success
        assert "网络错误" in result.error_message
    
    @pytest.mark.asyncio
    async def test_parse_batch(self, parser, mock_llm_manager):
        """测试批量解析"""
        images = [
            ImageInfo(url="https://example.com/1.jpg"),
            ImageInfo(url="https://example.com/2.jpg"),
            ImageInfo(url="https://example.com/3.jpg")
        ]
        
        results = await parser.parse_batch(images)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_llm_manager.generate_with_images.call_count == 3
    
    @pytest.mark.asyncio
    async def test_parse_with_default_provider(self, mock_llm_manager):
        """测试使用默认 provider"""
        parser = ImageParser(mock_llm_manager)  # 不指定 provider
        
        image_info = ImageInfo(url="https://example.com/image.jpg")
        result = await parser.parse(image_info)
        
        assert result.success
        
        # 验证调用参数
        call_args = mock_llm_manager.generate_with_images.call_args
        assert call_args[1]["provider_id"] is None
    
    def test_build_parse_prompt(self, parser):
        """测试构建解析提示词"""
        prompt = parser._build_parse_prompt()
        
        assert "请详细描述这张图片的内容" in prompt
        assert "主要物体和场景" in prompt
        assert "不超过200字" in prompt
