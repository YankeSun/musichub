"""
MusicHub Core - 核心功能模块

包含：
- downloader: 下载引擎（并发下载、断点续传、进度回调）
- metadata: 元数据管理（ID3 标签、专辑封面、歌词同步）
- converter: 格式转换（FLAC ↔ MP3 ↔ ALAC 等，基于 ffmpeg）
"""

from .downloader import (
    Downloader,
    DownloadTask,
    DownloadResult,
    DownloadStatus,
)

from .metadata import (
    MetadataManager,
    TrackMetadata,
    AudioFormat,
)

from .converter import (
    AudioConverter,
    ConversionOptions,
    ConversionResult,
    AudioQuality,
    convert_audio,
)

__all__ = [
    # Downloader
    "Downloader",
    "DownloadTask",
    "DownloadResult",
    "DownloadStatus",
    # Metadata
    "MetadataManager",
    "TrackMetadata",
    "AudioFormat",
    # Converter
    "AudioConverter",
    "ConversionOptions",
    "ConversionResult",
    "AudioQuality",
    "convert_audio",
]

__version__ = "0.1.0"
