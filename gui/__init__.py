"""
MusicHub GUI 模块
现代音乐下载管理器图形界面
"""

from .app import MainWindow, main
from .styles import STYLESHEET
from .widgets import (
    SearchResultItem,
    DownloadQueueItem,
    PlaylistItem,
    SettingsOption,
    LoadingSpinner,
    EmptyStateWidget
)

__all__ = [
    'MainWindow',
    'main',
    'STYLESHEET',
    'SearchResultItem',
    'DownloadQueueItem',
    'PlaylistItem',
    'SettingsOption',
    'LoadingSpinner',
    'EmptyStateWidget',
]

__version__ = '1.0.0'
