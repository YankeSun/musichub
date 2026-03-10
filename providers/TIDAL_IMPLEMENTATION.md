# Tidal 插件实现文档

## 概述

已成功为 MusicHub 实现 Tidal 平台插件，支持搜索、下载和元数据管理功能。

## 实现文件

### 主要文件

1. **`providers/tidal.py`** (31KB)
   - `TidalProvider` 类：实现 BaseProvider 接口
   - `TidalConfig` 类：配置管理
   - `TidalQuality` 枚举：音质等级定义

2. **`providers/__init__.py`**
   - 导出 TidalProvider 和 TidalConfig
   - 注册到 PROVIDERS 和 PROVIDER_CONFIGS 字典

3. **`providers/README.md`**
   - 更新支持的平台列表
   - 添加 Tidal 配置和使用示例

### 辅助文件

4. **`providers/examples/tidal_example.py`**
   - 完整的使用示例
   - 演示搜索、下载、元数据获取

5. **`tests/test_tidal.py`**
   - 单元测试覆盖
   - 包括配置、初始化、搜索、下载等测试

6. **`src/musichub/plugins/sources/tidal.py`** (30KB)
   - 备选实现（使用新的插件系统架构）
   - 支持 DASH 流下载

## 功能特性

### 搜索功能
- ✅ 歌曲搜索
- ✅ 专辑搜索（返回专辑内所有歌曲）
- ✅ 播放列表搜索（返回播放列表内所有歌曲）
- ✅ 支持分页和限制结果数量

### 音质支持
- ✅ **STANDARD**: 96kbps AAC (免费订阅)
- ✅ **HIGH**: 320kbps AAC (高级订阅)
- ✅ **LOSSLESS**: 16bit/44.1kHz FLAC (HiFi 订阅)
- ✅ **HI_RES**: 24bit/192kHz FLAC (HiFi Plus 订阅)

### 下载功能
- ✅ 获取流媒体 URL
- ✅ 支持 DASH manifest 解析
- ✅ 自动根据音质选择文件扩展名 (FLAC/M4A)
- ✅ 写入元数据（标题、艺术家、专辑、封面等）

### 元数据管理
- ✅ 获取歌曲详细信息
- ✅ 获取专辑信息
- ✅ 下载专辑封面
- ✅ 使用 mutagen 写入音频文件标签

### 认证支持
- ✅ API Token 认证
- ✅ 客户端凭证认证（默认配置）
- ✅ 自动令牌刷新
- ✅ 用户订阅状态检测

## 配置选项

```python
config = {
    # 认证（二选一）
    "api_token": "your_api_token",  # 方式 1
    "client_id": "km8T9pS355y7dd",  # 方式 2（默认）
    "client_secret": "...",          # 方式 2（默认）
    
    # 音质
    "quality": "LOSSLESS",  # LOW, HIGH, LOSSLESS, HI_RES
    
    # 其他
    "country_code": "US",
    "timeout": 30,
    "retry_times": 3,
}
```

## 使用示例

### 基本使用

```python
import asyncio
from pathlib import Path
from providers import create_provider, Quality

async def main():
    # 创建插件
    tidal = await create_provider("tidal")
    
    # 搜索
    results = await tidal.search("Bohemian Rhapsody")
    
    # 下载无损音质
    if results:
        result = await tidal.download(
            track_id=results[0].id,
            save_path=Path("./downloads"),
            quality=Quality.LOSSLESS
        )
        print(f"下载完成：{result.file_path}")
    
    await tidal.close()

asyncio.run(main())
```

### 获取专辑

```python
# 获取专辑所有音轨
album_tracks = await tidal.get_album_tracks("album_id")

# 获取播放列表
playlist_tracks = await tidal.get_playlist("playlist_id")
```

## 技术实现细节

### API 端点

- **认证**: `https://auth.tidal.com/v1/oauth2/token`
- **搜索**: `https://api.tidalhifi.com/v1/search`
- **音轨信息**: `https://api.tidalhifi.com/v1/tracks/{id}`
- **流 URL**: `https://api.tidalhifi.com/v1/tracks/{id}/playbackinfopostpaywall`
- **专辑音轨**: `https://api.tidalhifi.com/v1/albums/{id}/items`
- **播放列表**: `https://api.tidalhifi.com/v1/playlists/{id}/items`

### 流媒体处理

1. **直接 URL**（旧版 API）:
   - 响应包含 `streamUrl` 字段
   - 直接下载即可

2. **DASH Manifest**（新版 API）:
   - 响应包含 base64 编码的 manifest
   - 解析 XML 提取 `BaseURL` 或 `SegmentURL`
   - 下载所有片段并合并

3. **加密 MP4**:
   - 需要额外解密步骤
   - 当前实现返回错误提示

### 元数据写入

使用 `mutagen` 库支持多种格式：
- **FLAC**: Vorbis 注释 + embedded pictures
- **M4A**: MP4 原子标签
- **MP3**: ID3 标签

## 依赖

```bash
pip install httpx mutagen
```

## 测试

运行单元测试：

```bash
cd /root/.openclaw/workspace/projects/musichub
pytest tests/test_tidal.py -v
```

运行示例：

```bash
python providers/examples/tidal_example.py
```

## 已知限制

1. **加密内容**: 部分 HiFi Plus 内容使用加密 MP4，需要额外解密
2. **歌词**: 当前未实现歌词获取（需要额外 API 调用）
3. **并发控制**: 批量下载时需要自行控制并发数
4. **地区限制**: 部分内容可能因地区不可用

## 注意事项

1. **版权合规**: 请确保下载的音乐仅用于个人学习研究
2. **订阅要求**: 无损音质需要有效的 HiFi 或 HiFi Plus 订阅
3. **API 限制**: 避免频繁请求导致 IP 被封
4. **凭证安全**: 不要分享 API token 或客户端凭证

## 后续改进

- [ ] 实现歌词获取
- [ ] 支持加密 MP4 解密
- [ ] 添加批量下载队列管理
- [ ] 支持视频下载
- [ ] 添加进度回调
- [ ] 支持断点续传

## 参考资料

- [Tidal API 文档](https://developer.tidal.com/)
- [DASH Specification](https://dashif.org/)
- [mutagen 文档](https://mutagen.readthedocs.io/)
