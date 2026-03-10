# Apple Music 插件配置指南

## 概述

Apple Music 插件支持从 Apple Music 平台搜索、获取流媒体 URL 和下载无损音质音乐。

## 功能特性

- ✅ 搜索歌曲/专辑/播放列表/艺术家
- ✅ 获取音频流 URL
- ✅ 下载 ALAC 无损音质
  - LOSSLESS: 16bit/44.1kHz (CD 音质)
  - HI_RES: 24bit/192kHz (高解析度)
- ✅ Dolby Atmos 空间音频支持
- ✅ 完整元数据获取

## 配置要求

### 必需配置

1. **Apple Music API Token**
   - 用于访问 Apple Music API
   - 从 Apple Developer 门户获取

2. **Music User Token** (可选但推荐)
   - 用于获取流媒体 URL
   - 需要有效的 Apple Music 订阅账号

### 配置示例

```python
config = {
    # API 认证
    "api_token": "your_api_token_here",
    "music_user_token": "your_music_user_token_here",
    
    # 区域设置
    "country": "US",  # 或 CN, JP, UK 等
    "language": "en-US",
    
    # 音质设置
    "audio_quality": "lossless",  # standard, lossless, hi_res
    "spatial_audio": "stereo",    # stereo, dolby_atmos
    
    # 网络设置
    "timeout": 30,
    "max_retries": 3
}
```

## 使用方法

### 基本使用

```python
from musichub.providers import get_provider

# 创建插件实例
provider = get_provider("apple_music", config)

# 初始化
await provider.initialize()

# 搜索音乐
tracks = await provider.search("Taylor Swift", limit=10)

# 获取音轨详情
track_info = await provider.get_track_info("1234567890")

# 获取流媒体 URL
stream_url = await provider.get_stream_url("1234567890")

# 关闭插件
await provider.shutdown()
```

### 搜索专辑

```python
albums = await provider.search_albums("1989", limit=5)
for album in albums:
    print(f"{album['name']} - {album['artist']}")
    
# 获取专辑所有音轨
album_tracks = await provider.get_album_tracks(album_id)
```

### 搜索播放列表

```python
playlists = await provider.search_playlists("Today's Hits", limit=5)
for playlist in playlists:
    print(f"{playlist['name']} - {playlist['track_count']} tracks")
    
# 获取播放列表所有音轨
playlist_tracks = await provider.get_playlist_tracks(playlist_id)
```

### 获取艺术家热门歌曲

```python
artists = await provider.search_artists("Taylor Swift", limit=5)
if artists:
    top_songs = await provider.get_artist_top_songs(artists[0]["id"], limit=10)
```

### 音质选择

```python
from musichub.providers.apple_music import AudioQuality

# 获取高解析度无损音质
stream_url = await provider.get_stream_url(
    "1234567890",
    quality=AudioQuality.HI_RES
)

# 获取音质信息
quality_info = provider.get_quality_info(AudioQuality.HI_RES)
print(quality_info["description"])
# 输出：高解析度无损 (24bit/192kHz ALAC)
```

### Dolby Atmos 支持

```python
config = {
    "api_token": "your_token",
    "music_user_token": "your_user_token",
    "spatial_audio": "dolby_atmos"  # 启用空间音频
}

provider = get_provider("apple_music", config)
await provider.initialize()
```

## API Token 获取

### 步骤 1: 创建 Apple Developer 账号

1. 访问 [Apple Developer](https://developer.apple.com/)
2. 注册/登录账号
3. 加入 Apple Developer Program（需要付费）

### 步骤 2: 创建 API Key

1. 登录 [App Store Connect](https://appstoreconnect.apple.com/)
2. 进入 Users and Access → Keys
3. 点击 "+" 创建新密钥
4. 选择 Apple Music API 权限
5. 下载并保存 `.p8` 文件

### 步骤 3: 生成 JWT Token

使用以下代码生成 JWT Token：

```python
import jwt
import time

def generate_apple_music_token(key_id: str, team_id: str, private_key: str) -> str:
    """生成 Apple Music API JWT Token"""
    headers = {
        "alg": "ES256",
        "kid": key_id
    }
    
    payload = {
        "iss": team_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 15777000  # 6 个月
    }
    
    token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    return token
```

## Music User Token 获取

Music User Token 需要通过 Apple Music 网页播放器或 App 获取：

1. 打开 Apple Music 网页播放器 (music.apple.com)
2. 登录你的 Apple Music 账号
3. 打开浏览器开发者工具 (F12)
4. 在 Network 标签中查找包含 `music.163.com` 或 `apple.com` 的请求
5. 复制 `Authorization` header 中的 token

或者使用以下方法：

```python
# 通过 Apple Music 认证流程获取
# 需要使用 OAuth 2.0 流程
```

## 错误处理

```python
from musichub.providers.apple_music import (
    AppleMusicError,
    AuthenticationError,
    NotFoundError,
    RateLimitError
)

try:
    tracks = await provider.search("song name")
except AuthenticationError:
    print("认证失败，请检查 API Token")
except NotFoundError:
    print("未找到相关音乐")
except RateLimitError:
    print("请求过于频繁，请稍后再试")
except AppleMusicError as e:
    print(f"Apple Music 错误：{e}")
```

## 音质对比

| 音质等级 | 编码格式 | 比特率 | 采样率 | 位深 | 文件大小 (3 分钟) |
|---------|---------|--------|--------|------|------------------|
| STANDARD | AAC | 256 kbps | 44.1 kHz | 16 bit | ~5.6 MB |
| LOSSLESS | ALAC | 1411 kbps | 44.1 kHz | 16 bit | ~31 MB |
| HI_RES | ALAC | 4608 kbps | 192 kHz | 24 bit | ~101 MB |

## 注意事项

1. **订阅要求**: 获取流媒体 URL 需要有效的 Apple Music 订阅
2. **区域限制**: 某些内容可能因地区而异
3. **DRM 保护**: 部分音源可能受 DRM 保护，无法下载
4. **速率限制**: Apple Music API 有请求频率限制
5. **Token 有效期**: API Token 最长有效期为 6 个月

## 故障排除

### 认证失败

- 检查 API Token 是否正确
- 确认 Token 未过期
- 验证 Apple Developer 账号状态

### 无法获取流媒体 URL

- 确认 Music User Token 有效
- 检查 Apple Music 订阅状态
- 验证账号区域设置

### 搜索结果为空

- 检查搜索关键词
- 确认账号区域是否有该内容
- 尝试使用英文关键词搜索

## 支持的平台

- ✅ macOS
- ✅ Linux
- ✅ Windows

## 依赖

- Python 3.9+
- aiohttp
- pydantic
