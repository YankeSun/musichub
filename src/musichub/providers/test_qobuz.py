#!/usr/bin/env python3
"""
Qobuz Provider 单元测试

运行方式：
    cd /root/.openclaw/workspace/projects/musichub/src
    python3 musichub/providers/test_qobuz.py
"""

import sys
import asyncio
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入 qobuz 模块，绕过 musichub.__init__ 的循环导入
import importlib.util
spec = importlib.util.spec_from_file_location("qobuz", Path(__file__).parent / "qobuz.py")
qobuz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qobuz)


def test_config():
    """测试配置类"""
    print("测试 QobuzConfig...")
    
    # 测试默认配置
    config = qobuz.QobuzConfig()
    assert config.app_id == ""
    assert config.app_secret == ""
    assert config.audio_quality == qobuz.AudioQuality.HI_RES
    print("  ✓ 默认配置正确")
    
    # 测试从字典创建
    config = qobuz.QobuzConfig.from_dict({
        'app_id': '12345',
        'app_secret': 'abcde',
        'audio_quality': 'lossless',
        'country': 'FR'
    })
    assert config.app_id == '12345'
    assert config.app_secret == 'abcde'
    assert config.audio_quality == qobuz.AudioQuality.LOSSLESS
    assert config.country == 'FR'
    print("  ✓ 从字典创建配置正确")
    
    # 测试音质枚举
    assert qobuz.AudioQuality.STANDARD.value == "standard"
    assert qobuz.AudioQuality.LOSSLESS.value == "lossless"
    assert qobuz.AudioQuality.HI_RES.value == "hi_res"
    print("  ✓ AudioQuality 枚举正确")


def test_provider_init():
    """测试 Provider 初始化"""
    print("测试 QobuzProvider 初始化...")
    
    provider = qobuz.QobuzProvider({
        'app_id': 'test_app_id',
        'app_secret': 'test_app_secret'
    })
    
    assert provider.name == "qobuz"
    assert provider.version == "1.0.0"
    assert "Qobuz" in provider.description
    assert provider.config.app_id == 'test_app_id'
    assert provider.config.app_secret == 'test_app_secret'
    print("  ✓ Provider 属性正确")
    
    # 测试 validate_config
    assert provider.validate_config() == True
    print("  ✓ 配置验证通过")
    
    # 测试无效配置
    invalid_provider = qobuz.QobuzProvider({})
    assert invalid_provider.validate_config() == False
    print("  ✓ 无效配置被正确拒绝")


def test_quality_info():
    """测试音质信息"""
    print("测试音质信息...")
    
    provider = qobuz.QobuzProvider({'app_id': 'test', 'app_secret': 'test'})
    
    # 测试 STANDARD
    info = provider.get_quality_info(qobuz.AudioQuality.STANDARD)
    assert info['codec'] == 'MP3'
    assert info['bitrate'] == 320
    print(f"  ✓ STANDARD: {info['description']}")
    
    # 测试 LOSSLESS
    info = provider.get_quality_info(qobuz.AudioQuality.LOSSLESS)
    assert info['codec'] == 'FLAC'
    assert info['bitrate'] == 1411
    assert info['bit_depth'] == 16
    assert info['sample_rate'] == 44100
    print(f"  ✓ LOSSLESS: {info['bit_depth']}bit/{int(info['sample_rate']/1000)}kHz CD Quality")
    
    # 测试 HI_RES
    info = provider.get_quality_info(qobuz.AudioQuality.HI_RES)
    assert info['codec'] == 'FLAC'
    assert info['bit_depth'] == 24
    assert info['sample_rate'] == 192000
    print(f"  ✓ HI_RES: {info['bit_depth']}bit/{int(info['sample_rate']/1000)}kHz High-Resolution")


def test_signature():
    """测试签名生成"""
    print("测试签名生成...")
    
    provider = qobuz.QobuzProvider({
        'app_id': 'test',
        'app_secret': 'secret123'
    })
    
    # 测试签名生成（使用固定时间戳）
    timestamp = 1234567890
    signature = provider._generate_signature("/track/getFileUrl", timestamp)
    
    # 验证签名格式（应该是 32 字符的 MD5 哈希）
    assert len(signature) == 32
    assert all(c in '0123456789abcdef' for c in signature)
    print(f"  ✓ 签名格式正确：{signature[:16]}...")
    
    # 验证签名一致性
    signature2 = provider._generate_signature("/track/getFileUrl", timestamp)
    assert signature == signature2
    print("  ✓ 签名一致性正确")


def test_track_info_parsing():
    """测试音轨数据解析"""
    print("测试音轨数据解析...")
    
    provider = qobuz.QobuzProvider({'app_id': 'test', 'app_secret': 'test'})
    
    # 模拟 Hi-Res 音轨数据
    hi_res_track = {
        "id": 123456,
        "title": "Test Track",
        "duration": 240,
        "track_number": 1,
        "isrc": "USRC12345678",
        "performer": {
            "id": 789,
            "name": "Test Artist"
        },
        "album": {
            "id": 456,
            "title": "Test Album",
            "release_date_original": "2024-01-15",
            "maximum_bit_depth": 24,
            "maximum_sampling_rate": 192.0,
            "image": {
                "large": "https://example.com/cover.jpg"
            }
        }
    }
    
    track_info = provider._parse_track(hi_res_track)
    assert track_info is not None
    assert track_info.id == "123456"
    assert track_info.title == "Test Track"
    assert track_info.artist == "Test Artist"
    assert track_info.album == "Test Album"
    assert track_info.duration == 240
    assert track_info.audio_quality == qobuz.AudioQuality.HI_RES
    assert track_info.hi_res == True
    assert track_info.bit_depth == 24
    assert track_info.sample_rate == 192000
    assert track_info.codec == "FLAC"
    assert "Hi-Res" in track_info.hi_res_description
    print(f"  ✓ Hi-Res 音轨解析正确：{track_info.hi_res_description}")
    
    # 模拟 CD 音质音轨数据
    cd_track = {
        "id": 234567,
        "title": "CD Track",
        "duration": 180,
        "performer": {"name": "CD Artist"},
        "album": {
            "title": "CD Album",
            "maximum_bit_depth": 16,
            "maximum_sampling_rate": 44.1,
            "image": {}
        }
    }
    
    track_info = provider._parse_track(cd_track)
    assert track_info is not None
    assert track_info.audio_quality == qobuz.AudioQuality.LOSSLESS
    assert track_info.bit_depth == 16
    assert track_info.sample_rate == 44100
    assert track_info.hi_res == False
    print(f"  ✓ CD 音质音轨解析正确：{track_info.hi_res_description}")


async def test_async_methods():
    """测试异步方法（需要有效 API 凭证）"""
    print("测试异步方法（跳过实际 API 调用）...")
    
    provider = qobuz.QobuzProvider({
        'app_id': 'test_app_id',
        'app_secret': 'test_app_secret'
    })
    
    # 测试未初始化状态
    try:
        await provider.search("test")
        print("  ✗ 应该在未初始化时抛出异常")
    except qobuz.QobuzError as e:
        print(f"  ✓ 未初始化时正确抛出异常：{e}")
    
    # 测试 initialize（会使用无效凭证，预期失败）
    result = await provider.initialize()
    if result:
        print("  ! 初始化成功（使用了有效凭证？）")
        await provider.shutdown()
    else:
        print("  ✓ 无效凭证时初始化失败（预期行为）")


def test_create_provider():
    """测试工厂函数"""
    print("测试 create_provider 工厂函数...")
    
    provider = qobuz.create_provider({
        'app_id': 'factory_test',
        'app_secret': 'secret'
    })
    
    assert isinstance(provider, qobuz.QobuzProvider)
    assert provider.config.app_id == 'factory_test'
    print("  ✓ 工厂函数创建正确")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Qobuz Provider 单元测试")
    print("=" * 60)
    print()
    
    try:
        test_config()
        print()
        
        test_provider_init()
        print()
        
        test_quality_info()
        print()
        
        test_signature()
        print()
        
        test_track_info_parsing()
        print()
        
        test_create_provider()
        print()
        
        # 异步测试
        asyncio.run(test_async_methods())
        print()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
