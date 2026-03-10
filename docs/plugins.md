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

---

## 🎵 音源插件配置

MusicHub 支持多个音乐平台。以下是各平台的配置指南。

### 支持的平台

| 平台 | 插件名称 | 音质 | 需要订阅 |
|-----|---------|------|---------|
| Spotify | `spotify` | 最高 320kbps | Premium (部分功能) |
| Tidal | `tidal` | Hi-Res Lossless | HiFi / HiFi Plus |
| Apple Music | `apple_music` | Hi-Res Lossless | Apple Music |
| QQ 音乐 | `qq_music` | 母带音质 | VIP / VIP+ |
| 网易云音乐 | `netease` | Hi-Res | VIP / SVIP |

### 配置各平台插件

#### Spotify

```toml
[sources.spotify]
enabled = true
client_id = "你的 Spotify Client ID"
client_secret = "你的 Spotify Client Secret"
quality = "high"  # low, normal, high, very_high
```

**获取 API 凭证：**
1. 访问 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. 创建应用获取 Client ID 和 Secret
3. 运行 `musichub auth spotify` 完成 OAuth 认证

详细配置见 [Spotify 配置指南](platforms/spotify.md)

---

#### Tidal

```toml
[sources.tidal]
enabled = true
client_id = "你的 Tidal Client ID"
client_secret = "你的 Tidal Client Secret"
quality = "HI_RES"  # LOW, NORMAL, HIGH, HI_RES, HI_RES_LOSSLESS
country_code = "US"
```

**获取 API 凭证：**
1. 访问 [Tidal Developer Portal](https://developer.tidal.com/)
2. 创建应用获取 API Key
3. 需要 Tidal HiFi 订阅
4. 运行 `musichub auth tidal` 完成认证

详细配置见 [Tidal 配置指南](platforms/tidal.md)

---

#### Apple Music

```toml
[sources.apple_music]
enabled = true
key_id = "你的 Key ID"
issuer_id = "你的 Issuer ID"
team_id = "你的 Team ID"
private_key_path = "~/.config/musichub/AppleMusicKey.p8"
quality = "lossless"  # standard, high, lossless, hi_res_lossless
country = "US"
```

**获取 API 凭证：**
1. 加入 [Apple Developer Program](https://developer.apple.com/)
2. 在 App Store Connect 创建 MusicKit 密钥
3. 下载 `.p8` 私钥文件
4. 需要 Apple Music 订阅

详细配置见 [Apple Music 配置指南](platforms/apple_music.md)

---

#### QQ 音乐

```toml
[sources.qq_music]
enabled = true
cookie = "uin=xxx; qqmusic_key=xxx; ..."
quality = "hires"  # standard, high, hires, master
vip_enabled = true
```

**获取 Cookie：**
1. 访问 [QQ 音乐网页版](https://y.qq.com/)
2. 扫码登录
3. 从浏览器开发者工具复制 Cookie
4. 或运行 `musichub auth qqmusic` 自动获取

详细配置见 [QQ 音乐配置指南](platforms/qq_music.md)

---

#### 网易云音乐

```toml
[sources.netease]
enabled = true
cookie = "MUSIC_U=xxx; __csrf=xxx; ..."
quality = "lossless"  # standard, higher, exhigh, lossless, hires
vip_enabled = true
```

**获取 Cookie：**
1. 访问 [网易云音乐](https://music.163.com/)
2. 扫码或账号登录
3. 从浏览器复制 `MUSIC_U` Cookie
4. 或运行 `musichub auth netease` 自动获取

详细配置见 [网易云配置指南](platforms/netease.md)

---

### 多平台同时使用

你可以在配置中同时启用多个平台：

```toml
[sources.spotify]
enabled = true
# ... spotify 配置

[sources.tidal]
enabled = true
# ... tidal 配置

[sources.netease]
enabled = true
# ... netease 配置

# 默认使用的音源
default_source = "netease"
```

使用时指定音源：
```bash
musichub search "歌曲名" --source spotify
musichub download "链接" --source tidal
```

---

## 🧪 API 获取教程

### 通用步骤

大多数平台需要 API 凭证。通用流程：

1. **注册开发者账号**
   - 访问平台开发者网站
   - 使用普通账号登录或注册

2. **创建应用**
   - 填写应用名称和描述
   - 配置 Redirect URI（通常是 `http://localhost:8888/callback`）

3. **获取凭证**
   - Client ID / API Key
   - Client Secret / API Secret
   - 某些平台需要私钥文件（如 Apple Music）

4. **完成认证**
   - 运行 `musichub auth <平台名>`
   - 按提示完成 OAuth 流程

### 平台开发者入口

| 平台 | 开发者网站 |
|-----|-----------|
| Spotify | https://developer.spotify.com/ |
| Tidal | https://developer.tidal.com/ |
| Apple Music | https://developer.apple.com/ |
| QQ 音乐 | （使用 Cookie 认证） |
| 网易云音乐 | （使用 Cookie 认证） |

---

*最后更新：2026-03-10*
