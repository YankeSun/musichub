"""
MusicHub 基本使用示例

演示如何使用 DownloadEngine 进行搜索和下载
"""

import asyncio
from pathlib import Path

from musichub import DownloadEngine, Config


async def main():
    # 1. 创建配置
    config = Config(
        download_path=Path.home() / "Music" / "MusicHub",
        output_format="mp3",
        max_concurrent_downloads=5,
    )
    config.ensure_dirs()
    
    # 2. 初始化引擎
    engine = DownloadEngine(config)
    await engine.initialize()
    
    try:
        # 3. 搜索音乐
        print("🔍 搜索音乐...")
        results = await engine.search("周杰伦 七里香", limit=5)
        
        if not results:
            print("❌ 未找到结果")
            return
        
        # 显示结果
        for i, track in enumerate(results, 1):
            duration = f"{track.duration // 60}:{track.duration % 60:02d}" if track.duration else "N/A"
            print(f"{i}. {track.title} - {track.artist} ({duration})")
        
        # 4. 下载第一首
        track = results[0]
        print(f"\n📥 下载：{track.title}")
        
        # 注册进度回调
        def on_progress(event):
            if event.data.get('progress'):
                print(f"  进度：{event.data['progress']:.1f}%")
        
        engine.on(musichub.core.events.EventType.DOWNLOAD_PROGRESS, on_progress)
        
        result = await engine.download(track)
        
        if result.success:
            print(f"✅ 下载完成：{result.file_path}")
            print(f"   大小：{result.size_bytes / 1024 / 1024:.2f} MB")
            print(f"   耗时：{result.duration:.2f} 秒")
        else:
            print(f"❌ 下载失败：{result.error}")
        
        # 5. 批量下载示例
        # print("\n📦 批量下载...")
        # tracks = results[:3]  # 下载前 3 首
        # results = await engine.batch_download(tracks)
        # for i, (track, result) in enumerate(zip(tracks, results), 1):
        #     status = "✅" if result.success else "❌"
        #     print(f"{status} {i}. {track.title}")
    
    finally:
        # 6. 关闭引擎
        await engine.shutdown()
        print("\n👋 引擎已关闭")


if __name__ == "__main__":
    # 导入事件类型
    import musichub.core.events
    
    asyncio.run(main())
