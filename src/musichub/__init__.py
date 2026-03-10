"""
MusicHub - 插件化聚合音乐下载器

🎵 支持多平台音源、并发下载、多种导出格式
"""

__version__ = "0.1.0"
__author__ = "MusicHub Team"

from musichub.core.engine import DownloadEngine
from musichub.core.config import Config

__all__ = ["DownloadEngine", "Config"]
