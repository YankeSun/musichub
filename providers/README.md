# MusicHub 平台插件

统一的音乐平台插件接口，支持 QQ 音乐、网易云音乐、Spotify 和 Tidal。

## 快速开始

### 安装依赖

```bash
cd /root/.openclaw/workspace/projects/musichub
pip install -e .
```

### 基本使用

```python
import asyncio
from pathlib import Path
from providers import create_provider, Quality

async def main():
    # 创建 QQ 音乐插件
    qq = await create_provider("qq_music")
    
    # 搜索歌曲
    results = await qq.search("周杰伦 七里香")
    print(f"找到 {len(results)} 首歌曲")
    
    for track in results[:3]:
        print(f"  - {track}")
    
    # 下载歌曲
    if results:
        track = results[0]
        result = await qq.download(
            track_id=track.id,
            save_path=Path("./downloads"),
            quality=Quality.LOSSLESS
        )
        
        if result.success:
            print(f"下载完成：{result.file_path}")
        else:
            print(f"下载失败：{result.error}")
    
    # 获取元数据
    metadata = await qq.get_metadata(track.id)
    print(f"元数据：{metadata.title} - {metadata.artist}")
    
    # 关闭插件
    await qq.close()

asyncio.run(main())
```

### 使用网易云音乐

```python
from providers import create_provider, Quality

async def main():
    # 创建网易云音乐插件
    netease = await create_provider("netease")
    
    # 搜索
    results = await netease.search("陈奕迅")
    
    # 下载无损音质
    if results:
        result = await netease.download(
            track_id=results[0].id,
            save_path=Path("./music"),
            quality=Quality.LOSSLESS
        )
    
    await netease.close()

asyncio.run(main())
```

## 配置选项

### QQ 音乐配置

```python
config = {
    "cookie": "your_qq_music_cookie",  # 可选，用于访问 VIP 歌曲
    "uin": "1234567890",               # 可选，QQ 号
    "timeout": 30,                      # 请求超时 (秒)
    "retry_times": 3,                   # 重试次数
}

qq = await create_provider("qq_music", config)
```

### 网易云音乐配置

```python
config = {
    "cookie": "your_netease_cookie",   # 可选，用于访问 VIP 歌曲
    "timeout": 30,
    "retry_times": 3,
}

netease = await create_provider("netease", config)
```

### Tidal 配置

```python
config = {
    # 方式 1: 使用 API Token (如果你有)
    "api_token": "your_tidal_api_token",
    
    # 方式 2: 使用客户端凭证 (默认已配置，通常不需要修改)
    "client_id": "km8T9pS355y7dd",
    "client_secret": "66k2C6IZmV7cbrQUN99VqKzrN5WQ33J2oZ7Cz2b5sNA=",
    
    # 音质设置
    "quality": "LOSSLESS",  # 或 "HI_RES" (需要 HiFi Plus 订阅)
    
    # 其他配置
    "timeout": 30,
    "retry_times": 3,
    "country_code": "US",  # 国家/地区代码
}

tidal = await create_provider("tidal", config)
```

#### Tidal 音质说明

- **STANDARD**: 96kbps AAC (免费订阅)
- **HIGH**: 320kbps AAC (高级订阅)
- **LOSSLESS**: 16bit/44.1kHz FLAC (需要 HiFi 订阅)
- **HI_RES**: 24bit/192kHz FLAC (需要 HiFi Plus 订阅)

```python
# 下载无损音质
result = await tidal.download(
    track_id="12345678",
    save_path=Path("./downloads"),
    quality=Quality.LOSSLESS  # 或 Quality.HI_RES
)
```

## API 参考

### BaseProvider 接口

所有平台插件都实现以下方法：

- `async search(query: str, limit: int) -> List[TrackInfo]` - 搜索歌曲
- `async get_stream_url(track_id: str, quality: Quality) -> str` - 获取播放 URL
- `async download(track_id: str, save_path: Path, quality: Quality) -> DownloadResult` - 下载歌曲
- `async get_metadata(track_id: str) -> TrackMetadata` - 获取元数据
- `async get_playlist(playlist_id: str) -> List[TrackInfo]` - 获取歌单
- `async initialize() -> bool` - 初始化插件
- `async close()` - 关闭插件

### 音质选项

```python
from providers import Quality

Quality.STANDARD   # 标准品质 (128kbps MP3)
Quality.HIGH       # 高品质 (320kbps MP3)
Quality.LOSSLESS   # 无损 (FLAC)
Quality.HI_RES     # 高解析度 (24bit/96kHz+)
```

### 异常处理

```python
from providers import (
    ProviderError,
    SearchError,
    URLFetchError,
    DownloadError,
    MetadataError,
    AuthenticationError,
)

try:
    results = await provider.search("歌曲名")
except SearchError as e:
    print(f"搜索失败：{e}")
except AuthenticationError as e:
    print(f"认证失败，请检查配置")
except ProviderError as e:
    print(f"平台错误：{e}")
```

## 使用上下文管理器

```python
async with create_provider("qq_music") as qq:
    results = await qq.search("周杰伦")
    # 自动关闭
```

## 注意事项

1. **版权合规**: 请确保下载的音乐仅用于个人学习研究，不要用于商业用途
2. **API 限制**: 部分接口可能需要登录认证，请配置相应的 cookie
3. **音质可用性**: 不是所有歌曲都支持所有音质，下载前请检查 `quality_available`
4. **并发控制**: 批量下载时请控制并发数，避免触发平台反爬

## 扩展新平台

要添加新的音乐平台，只需继承 `BaseProvider` 并实现所有抽象方法：

```python
from providers import BaseProvider, TrackInfo, DownloadResult, TrackMetadata

class MyMusicProvider(BaseProvider):
    platform_name = "my_music"
    platform_display_name = "我的音乐平台"
    
    async def initialize(self) -> bool:
        # 初始化逻辑
        return True
    
    async def search(self, query: str, limit: int = 20) -> List[TrackInfo]:
        # 实现搜索
        pass
    
    async def get_stream_url(self, track_id: str, quality: Quality) -> str:
        # 获取播放 URL
        pass
    
    async def download(self, track_id: str, save_path: Path, quality: Quality) -> DownloadResult:
        # 实现下载
        pass
    
    async def get_metadata(self, track_id: str) -> TrackMetadata:
        # 获取元数据
        pass
    
    async def get_playlist(self, playlist_id: str) -> List[TrackInfo]:
        # 获取歌单
        pass
```

然后在 `providers/__init__.py` 中注册新平台。
