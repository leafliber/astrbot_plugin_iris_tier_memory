"""
Iris Tier Memory - 图片解析器

使用 LLM Vision 模型解析图片内容。
"""

from typing import List, TYPE_CHECKING

from iris_memory.core import get_logger
from iris_memory.config import get_config
from .models import ImageInfo, ParseResult

if TYPE_CHECKING:
    from iris_memory.llm.manager import LLMManager

logger = get_logger("image")


class ImageParser:
    """图片解析器
    
    使用支持 Vision 能力的 LLM 模型解析图片内容。
    
    Attributes:
        _llm_manager: LLM 调用管理器
        _provider: Provider ID（可选）
    
    Examples:
        >>> parser = ImageParser(llm_manager)
        >>> result = await parser.parse(image_info)
        >>> print(result.content)
    """
    
    def __init__(self, llm_manager: "LLMManager", provider: str = ""):
        """初始化图片解析器
        
        Args:
            llm_manager: LLM 调用管理器
            provider: Provider ID（留空使用配置或默认）
        """
        self._llm_manager = llm_manager
        self._provider = provider
    
    async def parse(self, image_info: ImageInfo) -> ParseResult:
        """解析单张图片
        
        Args:
            image_info: 图片信息
        
        Returns:
            解析结果
        """
        # 1. 检查图片来源
        image_url = None
        if image_info.has_url:
            image_url = image_info.url
        elif image_info.has_file_path:
            # 本地文件需要转为 data URL（这里简化处理，实际需要读取文件）
            logger.warning(f"本地图片暂不支持：{image_info.file_path}")
            return ParseResult(
                image_info=image_info,
                success=False,
                error_message="本地图片暂不支持"
            )
        else:
            return ParseResult(
                image_info=image_info,
                success=False,
                error_message="图片信息无效"
            )
        
        # 2. 构建解析提示词
        prompt = self._build_parse_prompt()
        
        # 3. 调用 LLM Vision
        try:
            response = await self._llm_manager.generate_with_images(
                prompt=prompt,
                image_urls=[image_url],
                module="image_parsing",
                provider_id=self._provider if self._provider else None
            )
            
            # 4. 返回结果
            return ParseResult(
                image_info=image_info,
                content=response,
                success=True
            )
        
        except Exception as e:
            logger.error(f"图片解析失败：{e}")
            return ParseResult(
                image_info=image_info,
                success=False,
                error_message=str(e)
            )
    
    async def parse_batch(self, images: List[ImageInfo]) -> List[ParseResult]:
        """批量解析图片
        
        Args:
            images: 图片信息列表
        
        Returns:
            解析结果列表
        """
        results = []
        for image in images:
            result = await self.parse(image)
            results.append(result)
        
        return results
    
    def _build_parse_prompt(self) -> str:
        """构建图片解析提示词
        
        Returns:
            解析提示词
        """
        return """请详细描述这张图片的内容。包括：
1. 主要物体和场景
2. 人物（如有）
3. 文字内容（如有）
4. 整体氛围和风格

请用简洁、准确的语言描述，不超过200字。"""
