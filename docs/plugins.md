# 插件开发指南

## 📦 插件类型

MusicHub 支持三种插件类型：

### 1. 音源插件 (Source Plugin)
负责从音乐平台搜索和获取音源信息。

### 2. 下载器插件 (Downloader Plugin)
负责实际的文件下载。

### 3. 导出器插件 (Exporter Plugin)
负责音频格式转换和元数据写入。

---

## 🔌 开发音源插件

### 1. 创建插件类

```python
# src/musichub/plugins/sources/mysource.py

from musichub.plugins.sources.base import SourcePluginBase
from musichub.core.engine import TrackInfo, StreamURL
from musichub.plugins.base import PluginMetadata


class MySource(SourcePluginBase):
    metadata = PluginMetadata(
        name="mysource",
        version="0.1.0",
        description="我的音乐源",
        author="Your Name",
    )
    
    async def initialize(self) -> None:
        await super().initialize()
        # 初始化 API 客户端等
    
    async def cleanup(self) -> None:
        # 清理资源
        await super().cleanup()
    
    async def search(self, query: str, limit: int = 20) -> list[TrackInfo]:
        # 实现搜索逻辑
        return [
            TrackInfo(
                id="track_001",
                title="歌曲名",
                artist="艺术家",
                album="专辑",
                duration=240,
                source=self.name,
            ),
        ]
    
    async def get_track_info(self, track_id: str) -> TrackInfo:
        # 获取详细信息
        pass
    
    async def get_stream_url(self, track_id: str) -> StreamURL:
        # 获取播放 URL
        return StreamURL(
            url="https://example.com/stream.mp3",
            quality="high",
            format="mp3",
        )
```

### 2. 注册插件

在 `pyproject.toml` 中添加：

```toml
[project.entry-points."musichub.sources"]
mysource = "musichub.plugins.sources.mysource:MySource"
```

---

## 📥 开发下载器插件

```python
# src/musichub/plugins/downloaders/mydownloader.py

from pathlib import Path
from typing import Callable

import httpx

from musichub.plugins.downloaders.base import DownloaderPluginBase
from musichub.core.engine import DownloadResult
from musichub.plugins.base import PluginMetadata


class MyDownloader(DownloaderPluginBase):
    metadata = PluginMetadata(
        name="mydownloader",
        version="0.1.0",
        description="自定义下载器",
    )
    
    supports_resume = True
    
    async def initialize(self) -> None:
        self._client = httpx.AsyncClient()
        await super().initialize()
    
    async def cleanup(self) -> None:
        await self._client.aclose()
        await super().cleanup()
    
    async def download(
        self,
        url: str,
        dest: Path,
        headers: dict[str, str] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadResult:
        # 实现下载逻辑
        async with self._client.stream('GET', url) as response:
            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest, 'wb') as f:
                async for chunk in response.aiter_bytes(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)
            
            return DownloadResult(
                success=True,
                file_path=dest,
                size_bytes=downloaded,
            )
```

注册：

```toml
[project.entry-points."musichub.downloaders"]
mydownloader = "musichub.plugins.downloaders.mydownloader:MyDownloader"
```

---

## 🎧 开发导出器插件

```python
# src/musichub/plugins/exporters/myexporter.py

from pathlib import Path

from musichub.plugins.exporters.base import ExporterPluginBase
from musichub.core.engine import TrackInfo
from musichub.plugins.base import PluginMetadata


class MyExporter(ExporterPluginBase):
    metadata = PluginMetadata(
        name="myexporter",
        version="0.1.0",
        description="自定义导出器",
    )
    
    supported_formats = ['myformat']
    
    async def export(
        self,
        input_file: Path,
        output_format: str,
        output_dir: Path | None = None,
        bitrate: str | None = None,
    ) -> Path:
        # 实现格式转换
        output_file = output_dir / f"{input_file.stem}.{output_format}"
        # 转换逻辑...
        return output_file
    
    async def write_metadata(
        self,
        file: Path,
        metadata: TrackInfo,
        cover_image: Path | None = None,
        lyrics: str | None = None,
    ) -> None:
        # 写入元数据
        pass
```

注册：

```toml
[project.entry-points."musichub.exporters"]
myexporter = "musichub.plugins.exporters.myexporter:MyExporter"
```

---

## 🧪 测试插件

```python
# tests/unit/test_mysource.py

import pytest
from musichub.plugins.sources.mysource import MySource


@pytest.mark.asyncio
async def test_mysource_search():
    plugin = MySource()
    await plugin.initialize()
    
    try:
        results = await plugin.search("测试", limit=5)
        assert len(results) > 0
        assert results[0].title is not None
    finally:
        await plugin.cleanup()
```

---

## 📝 最佳实践

1. **错误处理**: 捕获并妥善处理异常，返回有意义的错误信息
2. **资源管理**: 在 `cleanup()` 中释放所有资源
3. **配置验证**: 在 `validate_config()` 中验证用户配置
4. **日志记录**: 使用 `structlog` 记录关键操作
5. **并发安全**: 确保插件在并发环境下的安全性

---

## 🔍 调试技巧

1. 启用详细日志：`musichub -v search "query"`
2. 检查插件加载：查看启动时的日志输出
3. 单元测试：为关键逻辑编写测试用例

---

*最后更新：2026-03-10*
