#!/usr/bin/env python3
"""
Apple Music 插件独立测试脚本

用于验证 Apple Music 插件的基本功能
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "providers"))

# 使用 importlib 来加载模块，避免相对导入问题
import importlib.util

# 加载 base 模块
base_spec = importlib.util.spec_from_file_location("base", project_root / "providers" / "base.py")
base_module = importlib.util.module_from_spec(base_spec)
sys.modules['base'] = base_module
base_spec.loader.exec_module(base_module)

# 创建 providers 包模块
providers_pkg = type(sys)('providers')
providers_pkg.base = base_module
sys.modules['providers'] = providers_pkg
sys.modules['providers.base'] = base_module

# 现在加载 apple_music 模块
am_spec = importlib.util.spec_from_file_location("apple_music", project_root / "providers" / "apple_music.py")
apple_music_module = importlib.util.module_from_spec(am_spec)
sys.modules['apple_music'] = apple_music_module
sys.modules['providers.apple_music'] = apple_music_module
am_spec.loader.exec_module(apple_music_module)

# 导入需要的类
Quality = base_module.Quality
ProviderError = base_module.ProviderError
AppleMusicProvider = apple_music_module.AppleMusicProvider
AppleMusicConfig = apple_music_module.AppleMusicConfig
AppleMusicTrackInfo = apple_music_module.AppleMusicTrackInfo


def test_config():
    """测试配置类"""
    print("\n=== 测试配置类 ===")
    
    # 默认配置
    config = AppleMusicConfig()
    assert config.country == "US"
    assert config.language == "en-US"
    assert config.api_token == ""
    print("✅ 默认配置正确")
    
    # 自定义配置
    config = AppleMusicConfig(
        api_token="test_token",
        music_user_token="user_token",
        country="CN",
        language="zh-CN",
        spatial_audio=True
    )
    assert config.api_token == "test_token"
    assert config.music_user_token == "user_token"
    assert config.country == "CN"
    assert config.language == "zh-CN"
    assert config.spatial_audio is True
    print("✅ 自定义配置正确")
    
    # 配置验证
    assert config.validate() is True
    print("✅ 配置验证通过")
    
    # 缺少 Token 验证
    config_no_token = AppleMusicConfig()
    assert config_no_token.validate() is False
    print("✅ 缺少 Token 验证正确")


def test_provider_initialization():
    """测试插件初始化"""
    print("\n=== 测试插件初始化 ===")
    
    # 创建插件实例
    provider = AppleMusicProvider({
        "api_token": "test_token",
        "country": "US"
    })
    
    assert provider.platform_name == "apple_music"
    assert provider.platform_display_name == "Apple Music"
    print("✅ 插件属性正确")
    
    assert provider._initialized is False
    print("✅ 初始状态正确（未初始化）")


def test_quality_info():
    """测试音质信息"""
    print("\n=== 测试音质信息 ===")
    
    provider = AppleMusicProvider({"api_token": "test"})
    
    # 标准音质
    info = provider.get_quality_info(Quality.STANDARD)
    assert info["codec"] == "AAC"
    assert info["bitrate"] == 256
    print("✅ 标准音质信息正确")
    
    # 无损音质
    info = provider.get_quality_info(Quality.LOSSLESS)
    assert info["codec"] == "ALAC"
    assert info["bitrate"] == 1411
    assert info["sample_rate"] == 44100
    assert info["bit_depth"] == 16
    print("✅ 无损音质信息正确")
    
    # 高解析度音质
    info = provider.get_quality_info(Quality.HI_RES)
    assert info["codec"] == "ALAC"
    assert info["bitrate"] == 4608
    assert info["sample_rate"] == 192000
    assert info["bit_depth"] == 24
    print("✅ 高解析度音质信息正确")


def test_track_info_parsing():
    """测试音轨信息解析"""
    print("\n=== 测试音轨信息解析 ===")
    
    provider = AppleMusicProvider({"api_token": "test"})
    
    # 模拟 Apple Music API 响应
    track_data = {
        "id": "1234567890",
        "attributes": {
            "name": "Test Song",
            "artistName": "Test Artist",
            "albumName": "Test Album",
            "durationInMillis": 180000,
            "releaseDate": "2024-01-01",
            "genreNames": ["Pop"],
            "trackNumber": 1,
            "isrc": "USRC12345678",
            "composerName": "Test Composer",
            "artwork": {
                "url": "https://example.com/{w}x{h}.jpg"
            },
            "audioTraits": ["lossless-stereo"]
        }
    }
    
    track_info = provider._parse_track(track_data)
    
    assert track_info is not None
    assert track_info.id == "1234567890"
    assert track_info.title == "Test Song"
    assert track_info.artist == "Test Artist"
    assert track_info.album == "Test Album"
    assert track_info.duration == 180
    assert track_info.year == 2024
    assert track_info.isrc == "USRC12345678"
    assert track_info.composer == "Test Composer"
    assert track_info.cover_url == "https://example.com/1000x1000.jpg"
    print("✅ 音轨信息解析正确")
    
    # 测试 Hi-Res 音轨
    track_data_hires = {
        "id": "1234567891",
        "attributes": {
            "name": "Hi-Res Song",
            "artistName": "Test Artist",
            "audioTraits": ["hi-res-lossless", "dolby-atmos"]
        }
    }
    
    track_info_hires = provider._parse_track(track_data_hires)
    assert Quality.HI_RES in track_info_hires.quality_available
    assert track_info_hires.bitrate == 4608
    assert track_info_hires.sample_rate == 192000
    assert track_info_hires.bit_depth == 24
    print("✅ Hi-Res 音轨解析正确")


async def test_async_methods():
    """测试异步方法"""
    print("\n=== 测试异步方法 ===")
    
    provider = AppleMusicProvider({"api_token": "test"})
    
    # 测试未初始化时的错误
    try:
        await provider.search("test")
        assert False, "应该抛出 ProviderError"
    except ProviderError as e:
        assert "未初始化" in str(e)
        print("✅ 未初始化搜索正确抛出异常")
    
    try:
        await provider.get_stream_url("123")
        assert False, "应该抛出 ProviderError"
    except ProviderError as e:
        assert "未初始化" in str(e)
        print("✅ 未初始化获取 URL 正确抛出异常")


def test_track_info_dataclass():
    """测试 TrackInfo 数据类"""
    print("\n=== 测试 TrackInfo 数据类 ===")
    
    track = AppleMusicTrackInfo(
        id="123",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration=180
    )
    
    assert str(track) == "Test Artist - Test Song"
    print("✅ TrackInfo 字符串表示正确")
    
    assert track.quality_available == []
    assert track.extra == {}
    print("✅ TrackInfo 默认值正确")


def main():
    """主测试函数"""
    print("=" * 50)
    print("Apple Music 插件测试")
    print("=" * 50)
    
    try:
        test_config()
        test_provider_initialization()
        test_quality_info()
        test_track_info_parsing()
        asyncio.run(test_async_methods())
        test_track_info_dataclass()
        
        print("\n" + "=" * 50)
        print("✅ 所有测试通过!")
        print("=" * 50)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        return 1
    except Exception as e:
        print(f"\n❌ 意外错误：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
