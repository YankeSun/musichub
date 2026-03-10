# 网易云音乐平台配置指南

## 📋 概述

网易云音乐插件支持从网易云音乐平台搜索和下载音乐，包括 VIP、数字专辑和播客内容。

---

## 🔑 获取网易云音乐 API 凭证

### 方式 1: Cookie 认证（推荐）

#### 步骤 1: 登录网易云音乐网页版

1. 访问 [网易云音乐](https://music.163.com/)
2. 使用手机号、微信或微博登录

#### 步骤 2: 获取 Cookie

**Chrome/Edge 浏览器：**

1. 按 `F12` 打开开发者工具
2. 切换到 **Network**（网络）标签
3. 刷新页面
4. 点击 `music.163.com` 请求
5. 在 **Request Headers** 中复制 `Cookie` 字段

![获取 Cookie](https://developer.chrome.com/docs/devtools/network/resources/)

**关键 Cookie 字段：**
- `MUSIC_U` - 登录凭证（最重要）
- `__csrf` - CSRF 令牌
- `os` - 操作系统

---

### 方式 2: MusicHub 自动获取

```bash
musichub auth netease
```

流程：
1. 生成登录二维码
2. 使用网易云音乐 APP 扫码
3. 自动获取并保存 Cookie

---

### 方式 3: 账号密码（不推荐）

```bash
musichub auth netease --method password
# 按提示输入手机号和密码
```

> ⚠️ **安全提示**: 建议使用扫码登录，避免在命令行输入密码。

---

## ⚙️ 配置 MusicHub

### 方法 1: CLI 配置

```bash
# 使用 Cookie
musichub config set sources.netease.cookie "MUSIC_U=xxx; __csrf=xxx; ..."
musichub config set sources.netease.enabled true
musichub config set sources.netease.quality "lossless"

# 或使用自动认证
musichub auth netease
```

### 方法 2: 编辑配置文件

编辑 `~/.config/musichub/config.toml`：

```toml
[sources.netease]
enabled = true
cookie = "MUSIC_U=xxx; __csrf=xxx; os=xxx; ..."
quality = "lossless"  # standard, higher, exhigh, lossless, hires
vip_enabled = true
```

---

## 🎵 使用示例

```bash
# 搜索音乐
musichub search "陈奕迅" --source netease

# 下载单曲
musichub download "https://music.163.com/song?id=xxx" --format mp3

# 下载专辑（无损）
musichub download "https://music.163.com/album?id=xxx" --quality lossless

# 下载歌单
musichub download "https://music.163.com/playlist?id=xxx" --concurrency 5

# 下载播客/电台
musichub download "https://music.163.com/djradio?id=xxx" --type dj

# 下载 MV
musichub download "https://music.163.com/mv?id=xxx" --type mv
```

---

## 📊 音质等级

| 等级 | 名称 | 格式 | 比特率 | 要求 |
|-----|------|------|--------|------|
| standard | 标准 | MP3 | 128 kbps | 免费 |
| higher | 较高 | MP3 | 320 kbps | 免费 |
| exhigh | 极高 | AAC | 320 kbps | VIP |
| lossless | 无损 | FLAC | 16-bit/44.1kHz | VIP |
| hires | 高解析 | FLAC | 24-bit/48kHz+ | VIP/SVIP |

---

## 🎼 特殊功能

### VIP 内容

```toml
[sources.netease]
vip_enabled = true
```

VIP 可下载：
- 无损音质
- 付费数字专辑
- 独家内容

### 歌词下载

网易云音乐以歌词质量著称：

```bash
# 下载歌词
musichub download "xxx" --lyrics

# 下载歌词（含翻译）
musichub download "xxx" --lyrics --translate

# 仅下载歌词
musichub lyrics "xxx" --output lyrics.txt
```

### 歌单批量下载

```bash
# 下载整个歌单
musichub download "https://music.163.com/playlist?id=xxx" \
  --concurrency 5 \
  --skip-unavailable  # 跳过不可用歌曲
```

### 播客/电台

```bash
# 下载播客节目
musichub download "https://music.163.com/djradio?id=xxx" \
  --episodes 10  # 下载最新 10 集
```

---

## 📱 移动端认证

如需更高权限，可从手机 APP 获取 Cookie：

### Android

1. 使用 HttpCanary 等抓包工具
2. 捕获网易云音乐 APP 请求
3. 提取 `MUSIC_U` Cookie

### iOS

1. 使用 Stream 或 Proxyman 抓包
2. 配置 HTTPS 证书
3. 捕获请求获取 Cookie

---

## ⚠️ 注意事项

1. **Cookie 有效期**: `MUSIC_U` 会过期，需定期重新认证
2. **VIP 限制**: VIP 歌曲需要有效订阅
3. **数字专辑**: 部分专辑需单独购买
4. **区域限制**: 部分内容仅限中国大陆
5. **版权保护**: 灰色歌曲无法下载
6. **账号安全**: 不要分享 `MUSIC_U` Cookie

---

## 🐛 常见问题

### Q: Cookie 过期提示
A: 运行 `musichub auth netease` 重新扫码登录。

### Q: 歌曲显示"灰色"
A: 这是版权限制，无法下载。使用 `--skip-unavailable` 跳过。

### Q: VIP 歌曲无法下载
A: 确认 VIP 状态有效，重新获取 Cookie。

### Q: 下载失败：403 Forbidden
A: Cookie 可能已失效或 CSRF 令牌错误。重新认证。

### Q: 如何查看 VIP 状态？
A: 运行 `musichub status netease` 查看账号信息。

---

## 🔧 高级配置

### 使用代理

```toml
[sources.netease]
proxy = "http://127.0.0.1:7890"
```

### 下载目录按歌手分类

```toml
[sources.netease]
organize_by_artist = true
```

### 自动嵌入歌词

```toml
[sources.netease]
embed_lyrics = true  # 将歌词嵌入音频文件
```

### 下载限制

```toml
[sources.netease]
daily_limit = 200    # 每日下载限制
rate_limit = 15      # 每分钟请求数
```

---

## 🎯 实用技巧

### 批量下载收藏列表

```bash
# 下载"我喜欢的音乐"
musichub download "https://music.163.com/playlist?id=你的收藏 ID"
```

### 下载年度歌单

```bash
# 下载年度听歌报告歌单
musichub download "https://music.163.com/playlist?id=年度报告 ID"
```

### 搜索并下载

```bash
# 搜索并直接下载第一首
musichub search "周杰伦 七里香" --download --source netease
```

---

## 🔗 相关资源

- [网易云音乐网页版](https://music.163.com/)
- [网易云音乐 VIP](https://music.163.com/vip)
- [数字专辑](https://music.163.com/album/digital/)
- [播客中心](https://music.163.com/djradio)

---

*最后更新：2026-03-10*
