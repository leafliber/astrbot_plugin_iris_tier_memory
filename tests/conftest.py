"""Pytest 配置文件"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """临时数据目录 fixture"""
    return tmp_path / "data"
