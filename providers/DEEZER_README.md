# Deezer 平台插件

MusicHub 的 Deezer 平台插件，支持搜索、下载和元数据获取。

## 功能特性

- ✅ 歌曲/专辑/播放列表搜索
- ✅ 音频流 URL 获取
- ✅ 多音质下载支持
- ✅ 元数据获取（封面、歌词、专辑信息）
- ✅ 自动写入文件标签（ID3/FLAC Vorbis）
- ✅ 异步支持
- ✅ 完整的错误处理

## 音质支持

| 音质等级 | 格式 | 比特率 | 订阅要求 |
|---------|------|--------|---------|
| STANDARD | MP3 | 128kbps | 免费/付费 |
| HIGH | MP3 | 320kbps | Premium |
| LOSSLESS | FLAC | 无损 | HiFi |

## 配置要求

### 必需

- **Deezer 账号**：免费或付费账号
- **ARL Cookie**：用于认证，获取高音质流

### 获取 ARL Cookie

1. 登录 Deezer 网页版：https://www.deezer.com
2. 打开浏览器开发者工具（F12）
3. 进入 **Application** (Chrome) 或 **Storage** (Firefox)
4. 展开 **Cookies** → **https://www.deezer.com**
5. 找到名为 `arl` 的 cookie
6. 复制其 **Value** 值

```
arl=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 配置示例

```python
config = {
    "arl_cookie": "your_arl_cookie_value_here",
    "quality": "lossless",  # standard, high, lossless
    "timeout": 30,
    "language": "zh-CN",
}
```

## 使用方法

### 基本使用

```python
import asyncio
from pathlib import Path
from providers import create_provider, Quality

async def main():
    # 配置
    config = {
        "arl_cookie": "YOUR_ARL_COOKIE",
        "quality": "lossless",
    }
    
    # 创建并初始化插件
    provider = await create_provider("deezer", config)
    
    # 搜索歌曲
    results = await provider.search("Bohemian Rhapsody", limit=5)
    
    for track in results:
        print(f"{track.artist} - {track.title}")
    
    # 下载歌曲
    result = await provider.download(
        track_id=results[0].id,
        save_path=Path("./downloads"),
        quality=Quality.LOSSLESS,
    )
    
    if result.success:
        print(f"下载成功：{result.file_path}")
        print(f"文件大小：{result.file_size / 1024 / 1024:.2f} MB")
    
    # 清理资源
    await provider.close()

asyncio.run(main())
```

### 搜索

```python
# 搜索歌曲
tracks = await provider.search("歌曲名称", limit=20)

# 搜索专辑（通过搜索然后过滤）
results = await provider.search("专辑名称")
albums = [t for t in results if t.album == "专辑名称"]

# 获取专辑所有音轨
album_id = tracks[0].extra["album_id"]
album_tracks = await provider.get_album_tracks(album_id)
```

### 获取流 URL

```python
# 获取无损音质
url = await provider.get_stream_url(track_id, Quality.LOSSLESS)

# 获取高品质
url = await provider.get_stream_url(track_id, Quality.HIGH)

# 获取标准品质
url = await provider.get_stream_url(track_id, Quality.STANDARD)
```

### 获取元数据

```python
metadata = await provider.get_metadata(track_id)

print(f"标题：{metadata.title}")
print(f"艺术家：{metadata.artist}")
print(f"专辑：{metadata.album}")
print(f"年份：{metadata.year}")
print(f"音轨号：{metadata.track_number}")
print(f"封面：{len(metadata.cover_data)} 字节")
print(f"歌词：{'有' if metadata.lyrics else '无'}")
```

### 获取播放列表

```python
# 获取播放列表中的所有歌曲
playlist_id = "1362917935"  # Deezer 播放列表 ID
tracks = await provider.get_playlist(playlist_id)

for track in tracks:
    print(f"{track.artist} - {track.title}")
```

### 上下文管理器

```python
async with await create_provider("deezer", config) as provider:
    results = await provider.search("歌曲名称")
    # 自动清理资源
```

## 错误处理

插件定义了以下异常类：

```python
from providers import (
    ProviderError,      # 基类异常
    SearchError,        # 搜索失败
    URLFetchError,      # URL 获取失败
    DownloadError,      # 下载失败
    MetadataError,      # 元数据获取失败
    AuthenticationError, # 认证失败
)

try:
    results = await provider.search("歌曲")
except SearchError as e:
    print(f"搜索失败：{e}")
except AuthenticationError as e:
    print(f"认证失败，请检查 ARL Cookie: {e}")
except ProviderError as e:
    print(f"插件错误：{e}")
```

## 依赖

- **httpx**: HTTP 客户端库
- **mutagen**: 音频元数据处理

安装依赖：

```bash
pip install httpx mutagen
```

## 完整示例

查看 `examples/deezer_example.py` 获取完整的使用示例。

## 注意事项

1. **ARL Cookie 有效期**：ARL Cookie 会过期，如果下载失败请重新获取
2. **订阅限制**：无损音质需要 Deezer HiFi 订阅
3. **地区限制**：某些歌曲可能因地区限制无法访问
4. **速率限制**：避免短时间内大量请求，可能被暂时封禁
5. **仅供个人使用**：请遵守 Deezer 服务条款和当地版权法律

## 故障排除

### 无法获取高音质

- 检查 ARL Cookie 是否正确
- 确认你的订阅类型支持请求的音质
- 尝试重新获取 ARL Cookie

### 下载失败

- 检查网络连接
- 确认输出目录有写入权限
- 检查磁盘空间

### 搜索无结果

- 尝试使用英文关键词
- 检查关键词拼写
- 某些歌曲可能因版权原因不可用

## API 参考

### DeezerProvider

| 方法 | 描述 |
|-----|------|
| `initialize()` | 初始化插件 |
| `search(query, limit)` | 搜索歌曲 |
| `get_stream_url(track_id, quality)` | 获取流 URL |
| `download(track_id, save_path, quality)` | 下载歌曲 |
| `get_metadata(track_id)` | 获取元数据 |
| `get_playlist(playlist_id)` | 获取播放列表 |
| `get_album_tracks(album_id)` | 获取专辑音轨 |
| `close()` | 关闭插件 |

### Quality 枚举

```python
Quality.STANDARD   # 128kbps MP3
Quality.HIGH       # 320kbps MP3
Quality.LOSSLESS   # FLAC 无损
Quality.HI_RES     # 高解析度（映射到 LOSSLESS）
```

## 许可证

本插件仅供学习和研究使用。请支持正版音乐。
