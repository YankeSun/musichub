#!/usr/bin/env python3
"""
MusicHub 平台插件使用示例

运行前请确保已安装依赖:
    pip install -e .
"""

import asyncio
from pathlib import Path
from providers import (
    create_provider, 
    Quality, 
    SearchError, 
    DownloadError,
    AuthenticationError,
)


async def demo_qq_music():
    """QQ 音乐插件演示"""
    print("=" * 50)
    print("QQ 音乐插件演示")
    print("=" * 50)
    
    async with create_provider("qq_music") as qq:
        # 搜索歌曲
        print("\n🔍 搜索：周杰伦 七里香")
        try:
            results = await qq.search("周杰伦 七里香", limit=5)
            print(f"✓ 找到 {len(results)} 首歌曲\n")
            
            for i, track in enumerate(results, 1):
                print(f"{i}. {track}")
                print(f"   专辑：{track.album}")
                print(f"   时长：{track.duration}秒")
                print(f"   可用音质：{[q.value for q in track.quality_available]}")
                print()
            
            # 如果有结果，尝试获取元数据
            if results:
                track = results[0]
                print(f"📋 获取元数据：{track.title}")
                metadata = await qq.get_metadata(track.id)
                print(f"   标题：{metadata.title}")
                print(f"   歌手：{metadata.artist}")
                if metadata.lyrics:
                    print(f"   歌词：{len(metadata.lyrics)} 字符")
                print()
                
        except SearchError as e:
            print(f"✗ 搜索失败：{e}")
        except AuthenticationError as e:
            print(f"✗ 认证失败：{e}")


async def demo_netease():
    """网易云音乐插件演示"""
    print("=" * 50)
    print("网易云音乐插件演示")
    print("=" * 50)
    
    async with create_provider("netease") as netease:
        # 搜索歌曲
        print("\n🔍 搜索：陈奕迅")
        try:
            results = await netease.search("陈奕迅", limit=5)
            print(f"✓ 找到 {len(results)} 首歌曲\n")
            
            for i, track in enumerate(results, 1):
                print(f"{i}. {track}")
                print(f"   专辑：{track.album}")
                print(f"   时长：{track.duration}秒")
                print(f"   可用音质：{[q.value for q in track.quality_available]}")
                print()
            
            # 如果有结果，尝试获取元数据
            if results:
                track = results[0]
                print(f"📋 获取元数据：{track.title}")
                metadata = await netease.get_metadata(track.id)
                print(f"   标题：{metadata.title}")
                print(f"   歌手：{metadata.artist}")
                if metadata.lyrics:
                    print(f"   歌词：{len(metadata.lyrics)} 字符")
                if metadata.cover_data:
                    print(f"   封面：{len(metadata.cover_data)} 字节")
                print()
                
        except SearchError as e:
            print(f"✗ 搜索失败：{e}")
        except AuthenticationError as e:
            print(f"✗ 认证失败：{e}")


async def demo_download():
    """下载演示（需要实际文件路径）"""
    print("=" * 50)
    print("下载功能演示")
    print("=" * 50)
    
    # 创建下载目录
    download_dir = Path("./downloads_demo")
    download_dir.mkdir(exist_ok=True)
    
    async with create_provider("qq_music") as qq:
        print("\n📥 准备下载...")
        
        try:
            results = await qq.search("测试歌曲", limit=1)
            if results:
                track = results[0]
                print(f"下载：{track}")
                
                result = await qq.download(
                    track_id=track.id,
                    save_path=download_dir,
                    quality=Quality.HIGH,  # 高品质 MP3
                )
                
                if result.success:
                    print(f"✓ 下载成功")
                    print(f"   路径：{result.file_path}")
                    print(f"   大小：{result.file_size / 1024 / 1024:.2f} MB")
                    print(f"   音质：{result.quality.value}")
                else:
                    print(f"✗ 下载失败：{result.error}")
            else:
                print("未找到可下载的歌曲")
                
        except DownloadError as e:
            print(f"✗ 下载错误：{e}")
        except Exception as e:
            print(f"✗ 未知错误：{e}")


async def main():
    """主函数"""
    print("\n🎵 MusicHub 平台插件示例\n")
    
    # 运行演示
    await demo_qq_music()
    print()
    await demo_netease()
    print()
    # 取消下载演示（需要真实 API 访问）
    # await demo_download()
    
    print("\n✅ 演示完成\n")


if __name__ == "__main__":
    asyncio.run(main())
