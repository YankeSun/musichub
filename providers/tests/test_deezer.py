"""
Deezer 插件单元测试

测试插件的基本结构和接口，不需要实际 API 调用。
"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

def test_imports():
    """测试基本导入"""
    print("测试 1: 导入模块...")
    try:
        # 直接导入 deezer 模块，避免 __init__.py 导入其他插件
        import importlib.util
        deezer_path = Path(__file__).parent.parent / "deezer.py"
        spec = importlib.util.spec_from_file_location("deezer_module", deezer_path)
        
        # 需要先导入 base 模块
        base_path = Path(__file__).parent.parent / "base.py"
        base_spec = importlib.util.spec_from_file_location("base_module", base_path)
        base_module = importlib.util.module_from_spec(base_spec)
        sys.modules['providers.base'] = base_module
        base_spec.loader.exec_module(base_module)
        
        deezer_module = importlib.util.module_from_spec(spec)
        sys.modules['providers.deezer'] = deezer_module
        spec.loader.exec_module(deezer_module)
        
        # 保存引用供其他测试使用
        test_imports.deezer = deezer_module
        test_imports.base = base_module
        
        print("  ✓ 导入成功")
        return True
    except Exception as e:
        print(f"  ✗ 导入失败：{e}")
        return False


def test_provider_class():
    """测试插件类属性"""
    print("测试 2: 插件类属性...")
    deezer = test_imports.deezer
    
    DeezerProvider = deezer.DeezerProvider
    DeezerConfig = deezer.DeezerConfig
    
    # 检查类属性
    assert DeezerProvider.platform_name == "deezer", "platform_name 应该是 'deezer'"
    assert DeezerProvider.platform_display_name == "Deezer", "platform_display_name 应该是 'Deezer'"
    assert DeezerProvider.config_class == DeezerConfig, "config_class 应该是 DeezerConfig"
    
    print("  ✓ 类属性正确")
    return True


def test_config_class():
    """测试配置类"""
    print("测试 3: 配置类...")
    deezer = test_imports.deezer
    DeezerConfig = deezer.DeezerConfig
    
    # 测试默认配置
    config = DeezerConfig()
    assert config.quality == "lossless", "默认音质应该是 'lossless'"
    assert config.timeout == 30, "默认超时应该是 30"
    
    # 测试自定义配置
    config2 = DeezerConfig(
        arl_cookie="test_cookie",
        quality="high",
        timeout=60,
    )
    assert config2.arl_cookie == "test_cookie"
    assert config2.quality == "high"
    assert config2.timeout == 60
    
    print("  ✓ 配置类工作正常")
    return True


def test_quality_enum():
    """测试音质枚举"""
    print("测试 4: 音质枚举...")
    deezer = test_imports.deezer
    base = test_imports.base
    
    DeezerQuality = deezer.DeezerQuality
    QUALITY_MAP = deezer.QUALITY_MAP
    QUALITY_BITRATE = deezer.QUALITY_BITRATE
    Quality = base.Quality
    
    # 检查枚举值
    assert DeezerQuality.STANDARD.value == "standard"
    assert DeezerQuality.HIGH.value == "high"
    assert DeezerQuality.LOSSLESS.value == "lossless"
    
    # 检查映射
    assert QUALITY_MAP[Quality.STANDARD] == DeezerQuality.STANDARD
    assert QUALITY_MAP[Quality.HIGH] == DeezerQuality.HIGH
    assert QUALITY_MAP[Quality.LOSSLESS] == DeezerQuality.LOSSLESS
    
    # 检查比特率
    assert QUALITY_BITRATE[DeezerQuality.STANDARD] == 128
    assert QUALITY_BITRATE[DeezerQuality.HIGH] == 320
    assert QUALITY_BITRATE[DeezerQuality.LOSSLESS] == 1411
    
    print("  ✓ 音质枚举正确")
    return True


async def test_provider_initialization():
    """测试插件初始化（不实际连接）"""
    print("测试 5: 插件初始化...")
    deezer = test_imports.deezer
    DeezerProvider = deezer.DeezerProvider
    
    # 创建插件实例（不提供 ARL cookie，会警告但不应崩溃）
    provider = DeezerProvider({
        "arl_cookie": "",  # 空 cookie 用于测试
        "timeout": 5,
    })
    
    assert provider.platform_name == "deezer"
    assert provider._initialized == False
    
    # 尝试初始化（可能会失败，但不应该崩溃）
    try:
        success = await provider.initialize()
        # 没有 ARL cookie 时初始化可能成功也可能失败，但不应抛出异常
        print(f"  初始化结果：{'成功' if success else '失败（预期）'}")
    except Exception as e:
        print(f"  ✗ 初始化异常：{e}")
        return False
    
    # 清理
    await provider.close()
    
    print("  ✓ 插件初始化流程正常")
    return True


def test_provider_methods():
    """测试插件方法存在"""
    print("测试 6: 插件方法...")
    deezer = test_imports.deezer
    DeezerProvider = deezer.DeezerProvider
    
    # 检查必需方法存在
    required_methods = [
        'initialize',
        'search',
        'get_stream_url',
        'download',
        'get_metadata',
        'get_playlist',
        'close',
    ]
    
    for method in required_methods:
        assert hasattr(DeezerProvider, method), f"缺少方法：{method}"
        assert callable(getattr(DeezerProvider, method)), f"方法不可调用：{method}"
    
    print("  ✓ 所有必需方法存在")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Deezer 插件单元测试")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_provider_class,
        test_config_class,
        test_quality_enum,
        test_provider_initialization,
        test_provider_methods,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = asyncio.run(test())
            else:
                result = test()
            
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ 测试异常：{e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
