"""
音源插件
"""

from musichub.plugins.sources.base import SourcePlugin
from musichub.plugins.sources.tidal import TidalSourcePlugin, TidalQuality, create_plugin

__all__ = [
    "SourcePlugin",
    "TidalSourcePlugin",
    "TidalQuality",
    "create_plugin",
]
