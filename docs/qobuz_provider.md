# Qobuz Provider 使用指南

## 概述

Qobuz Provider 是 MusicHub 的音源插件，支持从 Qobuz 平台搜索和下载 Hi-Res 无损音质音乐。

## 功能特性

- **搜索**: 支持搜索歌曲、专辑、播放列表、艺术家
- **音质等级**:
  - `LOSSLESS`: 16bit/44.1kHz FLAC (CD Quality)
  - `HI_RES`: 24bit/192kHz FLAC (High-Resolution)
- **元数据**: 完整的音轨信息，包括 Hi-Res 认证标识
- **异步支持**: 所有 API 调用均为异步

## 配置要求

### 必需配置

1. **Qobuz Sublime+ 订阅**
   - 只有 Sublime+ 订阅才能获取流媒体 URL
   - 普通订阅只能搜索和预览

2. **API 凭证**
   - `app_id`: Qobuz 应用 ID
   - `app_secret`: Qobuz 应用密钥

### 获取 API 凭证

1. 访问 [Qobuz Developer Portal](https://www.qobuz.com/api)
2. 注册开发者账号
3. 创建新应用获取 `app_id` 和 `app_secret`

## 使用方法

### 基本配置

```python
from musichub.providers import get_provider

# 创建 Qobuz Provider 实例
provider = get_provider('qobuz', {
    'app_id': 'your_app_id',
    'app_secret': 'your_app_secret',
    'audio_quality': 'hi_res',  # 或 'lossless', 'standard'
    'country': 'US',  # 国家代码
    'timeout': 30,  # 请求超时（秒）
    'max_retries': 3  # 最大重试次数
})

# 初始化
if await provider.initialize():
    print("Qobuz 插件初始化成功")
else:
    print("初始化失败")
```

### 搜索音乐

```python
# 搜索歌曲
tracks = await provider.search("Bohemian Rhapsody", limit=10)
for track in tracks:
    print(f"{track.artist} - {track.title}")
    print(f"  音质：{track.hi_res_description}")
    print(f"  Hi-Res: {track.hi_res}")

# 搜索专辑
albums = await provider.search_albums("Dark Side of the Moon", limit=5)
for album in albums:
    print(f"{album['name']} - {album['artist']}")
    print(f"  Hi-Res: {album.get('hi_res', False)}")

# 搜索播放列表
playlists = await provider.search_playlists("Jazz Classics", limit=5)

# 搜索艺术家
artists = await provider.search_artists("Miles Davis", limit=5)
```

### 获取音轨详情

```python
track_info = await provider.get_track_info("123456789")
if track_info:
    print(f"标题：{track_info.title}")
    print(f"艺术家：{track_info.artist}")
    print(f"专辑：{track_info.album}")
    print(f"时长：{track_info.duration}秒")
    print(f"音质：{track_info.audio_quality.value}")
    print(f"Hi-Res: {track_info.hi_res}")
    print(f"比特深度：{track_info.bit_depth}bit")
    print(f"采样率：{track_info.sample_rate}Hz")
    print(f"编码：{track_info.codec}")
```

### 获取流媒体 URL

```python
# 获取默认音质的流媒体 URL
stream_url = await provider.get_stream_url("123456789")

# 指定音质
from musichub.providers.qobuz import AudioQuality

# Hi-Res 音质
stream_url = await provider.get_stream_url(
    "123456789",
    quality=AudioQuality.HI_RES
)

# CD 音质
stream_url = await provider.get_stream_url(
    "123456789",
    quality=AudioQuality.LOSSLESS
)
```

### 获取专辑所有音轨

```python
tracks = await provider.get_album_tracks("987654321")
for track in tracks:
    print(f"{track.track_number}. {track.title}")
```

### 获取播放列表所有音轨

```python
tracks = await provider.get_playlist_tracks("playlist_id")
for track in tracks:
    print(f"{track.artist} - {track.title}")
```

### 获取艺术家热门歌曲

```python
top_tracks = await provider.get_artist_top_tracks("artist_id", limit=20)
for track in top_tracks:
    print(f"{track.title}")
```

### 获取音质信息

```python
# 获取 HI_RES 音质详情
info = provider.get_quality_info(AudioQuality.HI_RES)
print(f"编码：{info['codec']}")
print(f"比特率：{info['bitrate']}kbps")
print(f"采样率：{info['sample_rate']}Hz")
print(f"比特深度：{info['bit_depth']}bit")
print(f"描述：{info['description']}")
```

### 关闭插件

```python
await provider.shutdown()
```

## 音质等级说明

| 等级 | 编码 | 比特深度 | 采样率 | 比特率 | 描述 |
|------|------|----------|--------|--------|------|
| STANDARD | MP3 | 16bit | 44.1kHz | 320kbps | 标准音质 |
| LOSSLESS | FLAC | 16bit | 44.1kHz | 1411kbps | CD 音质 |
| HI_RES | FLAC | 24bit | 192kHz | 4608kbps | Hi-Res 无损 |

## 错误处理

```python
from musichub.providers.qobuz import (
    QobuzError,
    AuthenticationError,
    SubscriptionError,
    NotFoundError,
    RateLimitError
)

try:
    track_info = await provider.get_track_info("invalid_id")
except AuthenticationError:
    print("认证失败：检查 app_id 和 app_secret")
except SubscriptionError:
    print("需要 Qobuz Sublime+ 订阅")
except NotFoundError:
    print("资源未找到")
except RateLimitError:
    print("请求过于频繁，请稍后重试")
except QobuzError as e:
    print(f"Qobuz 错误：{e}")
```

## 完整示例

```python
import asyncio
from musichub.providers import get_provider
from musichub.providers.qobuz import AudioQuality

async def main():
    # 创建并初始化 provider
    provider = get_provider('qobuz', {
        'app_id': 'your_app_id',
        'app_secret': 'your_app_secret',
        'audio_quality': 'hi_res'
    })
    
    if not await provider.initialize():
        print("初始化失败")
        return
    
    try:
        # 搜索音乐
        tracks = await provider.search("Pink Floyd", limit=5)
        
        for track in tracks:
            print(f"\n{track.artist} - {track.title}")
            print(f"  专辑：{track.album}")
            print(f"  音质：{track.hi_res_description}")
            
            # 获取流媒体 URL
            if track.hi_res:
                stream_url = await provider.get_stream_url(
                    track.id,
                    quality=AudioQuality.HI_RES
                )
                print(f"  流媒体 URL: {stream_url[:50]}...")
    
    finally:
        await provider.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## 注意事项

1. **订阅要求**: 获取流媒体 URL 需要 Qobuz Sublime+ 订阅
2. **地域限制**: 某些内容可能在特定国家/地区不可用
3. **API 限制**: Qobuz API 有速率限制，请合理使用
4. **版权**: 请遵守当地版权法律，仅下载合法授权的内容

## API 参考

完整 API 文档请参考：https://www.qobuz.com/api.json/0.2

## 故障排除

### 初始化失败

- 检查 `app_id` 和 `app_secret` 是否正确
- 确认网络连接正常
- 检查 Qobuz API 服务状态

### 获取流媒体 URL 失败

- 确认账号有 Sublime+ 订阅
- 检查音轨是否在订阅范围内
- 尝试降低音质等级

### 搜索结果为空

- 检查搜索关键词
- 尝试使用英文搜索
- 确认内容在你所在国家/地区可用

## 更新日志

### v1.0.0
- 初始版本
- 支持搜索、流媒体 URL 获取
- 支持 LOSSLESS 和 HI_RES 音质
- 完整的错误处理
- 异步支持
