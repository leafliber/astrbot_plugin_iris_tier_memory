"""认证中间件测试"""

import pytest
import jwt
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from iris_memory.web.auth import DashboardAuth


class TestDashboardAuth:
    """Dashboard 认证测试"""

    def test_init_default_config_path(self, tmp_path: Path):
        """测试默认配置路径初始化"""
        with patch('iris_memory.web.auth.Path') as mock_path:
            mock_path.return_value = tmp_path
            auth = DashboardAuth()
            assert auth.jwt_secret is None

    def test_load_jwt_secret_success(self, tmp_path: Path):
        """测试成功加载 JWT 密钥"""
        # 创建模拟配置文件
        config_file = tmp_path / "cmd_config.json"
        config_file.write_text('{"dashboard": {"jwt_secret": "test_secret_key"}}')
        
        with patch('iris_memory.web.auth.Path') as mock_path:
            mock_path.return_value = tmp_path
            auth = DashboardAuth()
            assert auth.jwt_secret == "test_secret_key"

    def test_load_jwt_secret_file_not_found(self, tmp_path: Path):
        """测试配置文件不存在"""
        with patch('iris_memory.web.auth.Path') as mock_path:
            mock_path.return_value = tmp_path
            auth = DashboardAuth()
            assert auth.jwt_secret is None

    def test_verify_token_valid(self):
        """测试有效 Token 验证"""
        auth = DashboardAuth()
        auth.jwt_secret = "test_secret"
        
        # 创建有效 Token
        payload = {
            "username": "admin",
            "exp": int(time.time()) + 3600  # 1小时后过期
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        result = auth.verify_token(token)
        assert result["username"] == "admin"

    def test_verify_token_expired(self):
        """测试过期 Token 验证"""
        auth = DashboardAuth()
        auth.jwt_secret = "test_secret"
        
        # 创建过期 Token
        payload = {
            "username": "admin",
            "exp": int(time.time()) - 3600  # 1小时前过期
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        with pytest.raises(ValueError, match="登录已过期"):
            auth.verify_token(token)

    def test_verify_token_invalid_signature(self):
        """测试无效签名 Token"""
        auth = DashboardAuth()
        auth.jwt_secret = "correct_secret"
        
        # 使用错误密钥创建 Token
        payload = {"username": "admin", "exp": int(time.time()) + 3600}
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        with pytest.raises(ValueError, match="无效Token"):
            auth.verify_token(token)

    def test_verify_token_no_secret_fallback(self):
        """测试无密钥时的降级验证"""
        auth = DashboardAuth()
        auth.jwt_secret = None
        auth.admin_username = "admin"
        
        # 创建 Token（无签名验证）
        payload = {
            "username": "admin",
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(payload, "any_secret", algorithm="HS256")
        
        # 应该能够验证（降级模式）
        result = auth.verify_token(token)
        assert result["username"] == "admin"

    def test_verify_token_wrong_user_fallback(self):
        """测试降级模式下非管理员用户"""
        auth = DashboardAuth()
        auth.jwt_secret = None
        auth.admin_username = "admin"
        
        payload = {
            "username": "guest",
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(payload, "any_secret", algorithm="HS256")
        
        with pytest.raises(ValueError, match="非管理员"):
            auth.verify_token(token)

    @pytest.mark.asyncio
    async def test_require_auth_decorator(self):
        """测试认证装饰器"""
        auth = DashboardAuth()
        auth.jwt_secret = "test_secret"
        
        # 模拟请求
        request = Mock()
        request.cookies = {"jwt_token": jwt.encode(
            {"username": "admin", "exp": int(time.time()) + 3600},
            "test_secret",
            algorithm="HS256"
        )}
        
        # 模拟被装饰的函数
        @auth.require_auth
        async def protected_route(request):
            return {"success": True}
        
        result = await protected_route(request)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_require_auth_missing_token(self):
        """测试缺少 Token 的认证"""
        auth = DashboardAuth()
        
        request = Mock()
        request.cookies = {}
        
        @auth.require_auth
        async def protected_route(request):
            return {"success": True}
        
        with pytest.raises(ValueError, match="缺少认证Token"):
            await protected_route(request)
