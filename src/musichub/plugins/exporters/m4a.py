"""
M4A 导出器插件

AAC/M4A 格式导出
"""

from __future__ import annotations

from pathlib import Path

from musichub.plugins.exporters.base import ExporterPluginBase
from musichub.core.engine import TrackInfo
from musichub.plugins.base import PluginMetadata
from musichub.utils.metadata import MetadataHandler


class M4AExporter(ExporterPluginBase):
    """
    M4A 导出器
    
    支持 AAC 编码的 M4A 格式
    """
    
    metadata = PluginMetadata(
        name="m4a",
        version="0.1.0",
        description="M4A/AAC 格式导出器",
    )
    
    supported_formats = ['m4a', 'aac']
    
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._metadata_handler = MetadataHandler()
    
    async def initialize(self) -> None:
        await super().initialize()
    
    async def cleanup(self) -> None:
        await super().cleanup()
    
    async def export(
        self,
        input_file: Path,
        output_format: str,
        output_dir: Path | None = None,
        bitrate: str | None = None,
    ) -> Path:
        """导出为 M4A 格式"""
        if output_format.lower() not in ('m4a', 'aac'):
            raise ValueError(f"M4AExporter 不支持格式：{output_format}")
        
        if not input_file.exists():
            raise FileNotFoundError(f"输入文件不存在：{input_file}")
        
        if output_dir is None:
            output_dir = input_file.parent
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{input_file.stem}.m4a"
        
        # TODO: 实现 M4A 转换（需要 ffmpeg）
        import shutil
        shutil.copy2(input_file, output_file)
        
        return output_file
    
    async def write_metadata(
        self,
        file: Path,
        metadata: TrackInfo,
        cover_image: Path | None = None,
        lyrics: str | None = None,
    ) -> None:
        """写入 M4A 元数据"""
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
