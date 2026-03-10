"""
MP3 导出器插件

MP3 格式转换和元数据写入
"""

from __future__ import annotations

import shutil
from pathlib import Path

from musichub.plugins.exporters.base import ExporterPluginBase
from musichub.core.engine import TrackInfo
from musichub.plugins.base import PluginMetadata
from musichub.utils.metadata import MetadataHandler


class MP3Exporter(ExporterPluginBase):
    """
    MP3 导出器
    
    支持：
    - MP3 格式输出
    - ID3 元数据写入
    - 封面嵌入
    - 歌词嵌入
    """
    
    metadata = PluginMetadata(
        name="mp3",
        version="0.1.0",
        description="MP3 格式导出器",
    )
    
    supported_formats = ['mp3']
    
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._metadata_handler = MetadataHandler()
    
    async def initialize(self) -> None:
        """初始化导出器"""
        await super().initialize()
    
    async def cleanup(self) -> None:
        """清理资源"""
        await super().cleanup()
    
    async def export(
        self,
        input_file: Path,
        output_format: str,
        output_dir: Path | None = None,
        bitrate: str | None = None,
    ) -> Path:
        """
        导出为 MP3 格式
        
        Args:
            input_file: 输入文件
            output_format: 输出格式（应为 'mp3'）
            output_dir: 输出目录
            bitrate: 比特率（如 '320k'）
        
        Returns:
            输出文件路径
        """
        if output_format.lower() != 'mp3':
            raise ValueError(f"MP3Exporter 不支持格式：{output_format}")
        
        if not input_file.exists():
            raise FileNotFoundError(f"输入文件不存在：{input_file}")
        
        # 确定输出路径
        if output_dir is None:
            output_dir = input_file.parent
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{input_file.stem}.mp3"
        
        # 如果已经是 MP3，直接复制
        if input_file.suffix.lower() == '.mp3':
            shutil.copy2(input_file, output_file)
            return output_file
        
        # TODO: 实现格式转换（需要 ffmpeg）
        # 目前简单复制，实际使用需要集成 ffmpeg
        shutil.copy2(input_file, output_file)
        
        return output_file
    
    async def write_metadata(
        self,
        file: Path,
        metadata: TrackInfo,
        cover_image: Path | None = None,
        lyrics: str | None = None,
    ) -> None:
        """
        写入 MP3 元数据
        
        Args:
            file: MP3 文件路径
            metadata: 音轨元数据
            cover_image: 封面图片路径
            lyrics: 歌词文本
        """
        if not file.exists():
            raise FileNotFoundError(f"文件不存在：{file}")
        
        self._metadata_handler.write_metadata(
            file=file,
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.album,
            cover_image=cover_image,
            lyrics=lyrics,
        )
