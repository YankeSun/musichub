# Spotify 插件文档

## 概述

Spotify 插件为 MusicHub 提供 Spotify 平台的音乐搜索、下载和元数据获取功能。

## 功能特性

### 核心功能

- ✅ **音乐搜索**: 搜索歌曲、专辑、播放列表
- ✅ **流媒体 URL 获取**: 获取歌曲播放链接
- ✅ **歌曲下载**: 通过 spotDL 集成实现下载
- ✅ **元数据获取**: 封面、歌词、专辑信息
- ✅ **歌单支持**: 获取播放列表歌曲列表
- ✅ **专辑支持**: 获取专辑完整曲目
- ✅ **艺术家支持**: 获取艺术家热门歌曲

### 音质支持

| 音质等级 | 比特率 | 说明 |
|---------|--------|------|
| STANDARD | 128kbps | 标准品质 MP3 |
| HIGH | 320kbps | 高品质 MP3 |
| LOSSLESS | 320kbps | 降级为 HIGH (Spotify 无真正无损) |
| HI_RES | 320kbps | 降级为 HIGH (Spotify 无真正无损) |

**注意**: Spotify 不提供真正的无损音质，LOSSLESS 和 HI_RES 会自动降级为 320kbps。

## 安装依赖

### 基础依赖

```bash
pip install httpx
```

### 可选依赖 (用于下载功能)

```bash
pip install spotdl
```

spotDL 用于实际的音频下载和元数据嵌入。它会:
- 从 Spotify 获取元数据
- 从 YouTube Music 获取音频
- 自动嵌入封面和歌词

## 配置

### 获取 Spotify API 凭证

1. 访问 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. 登录 Spotify 账号
3. 创建新应用
4. 获取 **Client ID** 和 **Client Secret**

### 配置选项

```python
config = {
    # 必需 (用于 API 访问)
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    
    # 可选
    "use_premium": False,      # 是否使用 Premium 账号
    "cookie": None,            # Spotify 认证 cookie
    "timeout": 30,             # 请求超时时间 (秒)
    "retry_times": 3,          # 重试次数
    "proxy": None,             # 代理地址
}
```

## 使用示例

### 基本使用

```python
import asyncio
from pathlib import Path
from providers.spotify import SpotifyProvider
from providers.base import Quality

async def main():
    # 配置
    config = {
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
    }
    
    # 创建并初始化插件
    provider = SpotifyProvider(config)
    await provider.initialize()
    
    # 搜索歌曲
    results = await provider.search("Bohemian Rhapsody", limit=5)
    
    for track in results:
        print(f"{track.artist} - {track.title}")
    
    # 下载歌曲
    result = await provider.download(
        track_id=results[0].id,
        save_path=Path("./downloads"),
        quality=Quality.HIGH,
    )
    
    if result.success:
        print(f"下载完成：{result.file_path}")
    
    # 关闭插件
    await provider.close()

asyncio.run(main())
```

### 搜索歌曲

```python
results = await provider.search("Queen Bohemian Rhapsody", limit=10)

for track in results:
    print(f"ID: {track.id}")
    print(f"标题：{track.title}")
    print(f"艺术家：{track.artist}")
    print(f"专辑：{track.album}")
    print(f"时长：{track.duration}秒")
    print(f"封面：{track.cover_url}")
```

### 获取歌曲元数据

```python
metadata = await provider.get_metadata("4u7EnebtmKWzUH433cf5Qv")

print(f"标题：{metadata.title}")
print(f"艺术家：{metadata.artist}")
print(f"专辑：{metadata.album}")
print(f"曲目号：{metadata.track_number}")
print(f"封面数据：{'有' if metadata.cover_data else '无'}")
print(f"歌词：{'有' if metadata.lyrics else '无'}")
```

### 下载歌曲

```python
from pathlib import Path

result = await provider.download(
    track_id="4u7EnebtmKWzUH433cf5Qv",
    save_path=Path("./downloads"),
    quality=Quality.HIGH,  # STANDARD 或 HIGH
)

if result.success:
    print(f"下载成功：{result.file_path}")
    print(f"文件大小：{result.file_size} 字节")
    print(f"音质：{result.quality.value}")
else:
    print(f"下载失败：{result.error}")
```

### 获取歌单

```python
# 获取播放列表歌曲
playlist_id = "37i9dQZF1DXcBWIGoYBM5M"  # Today's Top Hits
tracks = await provider.get_playlist(playlist_id)

print(f"歌单包含 {len(tracks)} 首歌曲:")
for track in tracks:
    print(f"  - {track.artist} - {track.title}")
```

### 获取专辑

```python
# 获取专辑完整曲目
album_id = "6akEvsycLGftJxYudPjmqK"
tracks = await provider.get_album(album_id)

print(f"专辑包含 {len(tracks)} 首歌曲:")
for track in tracks:
    print(f"  {track.track_number}. {track.title}")
```

### 获取艺术家热门歌曲

```python
# 获取艺术家热门歌曲
artist_id = "1dfeR4HaWDbWqFHLkxsg1d"  # Queen
tracks = await provider.get_artist_top_tracks(artist_id)

print(f"热门歌曲:")
for track in tracks:
    print(f"  - {track.title} (热度：{track.extra.get('popularity', 0)})")
```

### 解析 Spotify URL

```python
# 支持多种 URL 格式
urls = [
    "https://open.spotify.com/track/4u7EnebtmKWzUH433cf5Qv",
    "spotify:album:6akEvsycLGftJxYudPjmqK",
    "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
]

for url in urls:
    parsed = provider.parse_spotify_url(url)
    if parsed:
        print(f"类型：{parsed['type']}, ID: {parsed['id']}")
```

## API 参考

### SpotifyProvider 类

#### 初始化

```python
provider = SpotifyProvider(config: Optional[Dict[str, Any]] = None)
```

#### 方法

| 方法 | 说明 |
|------|------|
| `async initialize() -> bool` | 初始化插件 |
| `async search(query: str, limit: int) -> List[TrackInfo]` | 搜索歌曲 |
| `async get_stream_url(track_id: str, quality: Quality) -> str` | 获取流媒体 URL |
| `async download(track_id: str, save_path: Path, quality: Quality) -> DownloadResult` | 下载歌曲 |
| `async get_metadata(track_id: str) -> TrackMetadata` | 获取元数据 |
| `async get_playlist(playlist_id: str) -> List[TrackInfo]` | 获取歌单 |
| `async get_album(album_id: str) -> List[TrackInfo]` | 获取专辑 |
| `async get_artist_top_tracks(artist_id: str) -> List[TrackInfo]` | 获取艺术家热门歌曲 |
| `parse_spotify_url(url: str) -> Optional[Dict]` | 解析 Spotify URL |
| `async close()` | 关闭插件 |

### 异常类

| 异常 | 说明 |
|------|------|
| `ProviderError` | 插件基类异常 |
| `SearchError` | 搜索失败 |
| `URLFetchError` | URL 获取失败 |
| `DownloadError` | 下载失败 |
| `MetadataError` | 元数据获取失败 |
| `AuthenticationError` | 认证失败 |

## 限制和注意事项

### 音质限制

- Spotify **不提供真正的无损音质**
- 最高音质为 320kbps (HIGH)
- LOSSLESS 和 HI_RES 请求会自动降级为 HIGH

### API 限制

- 未认证请求有速率限制
- 建议使用 Client ID/Secret 进行认证
- Premium 账号可能获得更好的音质

### 下载限制

- 下载功能依赖 spotDL
- spotDL 从 YouTube Music 获取音频
- 实际音质取决于 YouTube Music 源

### 地区限制

- 某些歌曲可能因地区限制不可用
- 使用代理可能解决地区限制问题

## 故障排除

### 常见问题

#### 1. 认证失败

**错误**: `AuthenticationError: 获取 Spotify API 令牌失败`

**解决**:
- 检查 Client ID 和 Client Secret 是否正确
- 确认应用已在 Spotify Developer Dashboard 创建
- 检查网络连接

#### 2. 下载失败

**错误**: `DownloadError: spotDL 下载失败`

**解决**:
- 安装 spotDL: `pip install spotdl`
- 检查输出目录是否有写权限
- 尝试使用 STANDARD 音质

#### 3. 搜索无结果

**错误**: 搜索返回空列表

**解决**:
- 检查搜索关键词
- 确认歌曲在 Spotify 上可用
- 检查 API 认证状态

#### 4. 歌曲不可用

**错误**: `URLFetchError: 音源不可用`

**解决**:
- 歌曲可能有地区限制
- 尝试使用代理
- 歌曲可能已从 Spotify 下架

## 完整示例

查看 `example_usage_spotify.py` 获取完整的使用示例。

## 许可证

本插件遵循 MusicHub 项目的许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！
