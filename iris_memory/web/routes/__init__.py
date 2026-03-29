"""
API 路由模块

提供三类API：
- Memory API: 记忆管理（L1/L2/L3）
- Profile API: 画像管理
- Stats API: 统计数据
"""
from .memory import memory_bp
from .profile import profile_bp
from .stats import stats_bp

__all__ = ['memory_bp', 'profile_bp', 'stats_bp']
