# Tidal 平台配置指南

## 📋 概述

Tidal 插件提供高保真和无损音乐下载支持。Tidal 以提供 HiFi 和 Master Quality 音频而闻名。

---

## 🔑 获取 Tidal API 凭证

### 步骤 1: 创建 Tidal Developer 账号

1. 访问 [Tidal Developer Portal](https://developer.tidal.com/)
2. 使用你的 Tidal 账号登录（需要先有 Tidal 订阅）
3. 如果没有开发者账号，点击 **"Sign Up"** 注册

### 步骤 2: 创建应用

1. 登录后进入 **Dashboard**
2. 点击 **"Create New App"**
3. 填写应用信息：
   - **App Name**: MusicHub
   - **Description**: Personal music downloader
   - **Website URL**: （可选）
   - **Redirect URI**: `http://localhost:8080/tidal/callback`

### 步骤 3: 获取凭证

应用创建后，你将获得：
- **Client ID** (API Key)
- **Client Secret** (API Secret)

![Tidal Developer Dashboard](https://developer.tidal.com/assets/dashboard.png)

---

## 📝 订阅要求

Tidal API 需要有效的 Tidal 订阅：

| 订阅类型 | 音质 | API 访问 |
|---------|------|---------|
| Tidal HiFi | 16-bit/44.1kHz FLAC | ✅ |
| Tidal HiFi Plus | 24-bit/192kHz MQA | ✅ |
| Free Trial | 标准音质 | ⚠️ 有限制 |

> 💡 **建议**: 使用 HiFi Plus 订阅以获得最佳音质体验。

---

## ⚙️ 配置 MusicHub

### 方法 1: CLI 配置

```bash
musichub config set sources.tidal.client_id "你的 Client ID"
musichub config set sources.tidal.client_secret "你的 Client Secret"
musichub config set sources.tidal.enabled true
musichub config set sources.tidal.quality "HI_RES"
```

### 方法 2: 编辑配置文件

编辑 `~/.config/musichub/config.toml`：

```toml
[sources.tidal]
enabled = true
client_id = "你的 Client ID"
client_secret = "你的 Client Secret"
quality = "HI_RES"  # LOW, NORMAL, HIGH, HI_RES, HI_RES_LOSSLESS
country_code = "US"  # 你的国家代码
```

---

## 🔐 认证流程

Tidal 使用 OAuth 2.0 认证：

```bash
musichub auth tidal
```

流程：
1. 浏览器打开 Tidal 登录页面
2. 使用你的 Tidal 账号登录
3. 授权 MusicHub 访问
4. 自动保存访问令牌

---

## 🎵 使用示例

```bash
# 搜索音乐
musichub search "Daft Punk" --source tidal

# 下载单曲（Hi-Res）
musichub download "https://tidal.com/browse/track/xxx" --format flac

# 下载专辑
musichub download "https://tidal.com/browse/album/xxx" --quality HI_RES

# 下载艺术家全部作品
musichub download "https://tidal.com/browse/artist/xxx" --concurrency 3
```

---

## 📊 音质等级

| 等级 | 格式 | 比特率/采样率 | 订阅要求 |
|-----|------|--------------|---------|
| LOW | AAC | 96 kbps | Free |
| NORMAL | AAC | 320 kbps | Premium |
| HIGH | FLAC | 16-bit/44.1kHz | HiFi |
| HI_RES | FLAC | 24-bit/96kHz | HiFi Plus |
| HI_RES_LOSSLESS | FLAC | 24-bit/192kHz | HiFi Plus |

---

## 🎼 特殊功能

### Master Quality (MQA)

Tidal 的 Master Quality 音频使用 MQA 编码：

```toml
[sources.tidal]
prefer_master = true  # 优先下载 Master 版本
```

### Dolby Atmos

部分曲目支持 Dolby Atmos 空间音频：

```bash
musichub download "xxx" --atmos  # 下载 Atmos 版本（如果可用）
```

---

## ⚠️ 注意事项

1. **订阅验证**: API 会验证你的订阅状态
2. **区域限制**: 内容可用性因地区而异
3. **下载限制**: Tidal 对 API 调用有速率限制
4. **版权保护**: 遵守 Tidal 服务条款和版权法

---

## 🐛 常见问题

### Q: 401 Unauthorized 错误
A: 检查订阅是否过期，或重新认证：`musichub auth tidal --refresh`

### Q: 某些歌曲无法下载
A: 可能是区域限制或版权限制。尝试更改 `country_code` 配置。

### Q: 如何确认音质？
A: 下载后查看文件属性，或添加 `--verbose` 参数查看详细信息。

---

## 🔗 相关资源

- [Tidal API 文档](https://developer.tidal.com/documentation)
- [Tidal 音质说明](https://support.tidal.com/hc/en-us/articles/228023448-Audio-quality-in-the-TIDAL-music-service)
- [MQA 技术介绍](https://mqa.co.uk/)

---

*最后更新：2026-03-10*
