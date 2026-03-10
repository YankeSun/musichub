"""
Deezer 插件使用示例

展示如何使用 MusicHub 的 Deezer 插件进行搜索、下载和元数据获取。
"""

import asyncio
from pathlib import Path

from providers import create_provider, Quality, DeezerConfig


async def main():
    # 配置 Deezer 插件
    # 注意：你需要提供有效的 ARL Cookie 才能获取高音质
    # 获取方法:
    # 1. 登录 Deezer 网页版 (https://www.deezer.com)
    # 2. 打开浏览器开发者工具 (F12)
    # 3. 进入 Application/Storage -> Cookies
    # 4. 找到 arl cookie 并复制其值
    config = {
        "arl_cookie": "YOUR_ARL_COOKIE_HERE",  # 替换为你的 ARL Cookie
        "quality": "lossless",  # standard, high, lossless
        "timeout": 30,
    }
    
    # 创建并初始化插件
    print("正在初始化 Deezer 插件...")
    provider = await create_provider("deezer", config)
    print(f"✓ Deezer 插件初始化成功")
    print(f"  订阅类型：{provider._subscription_type}")
    print()
    
    # ========== 搜索歌曲 ==========
    print("=" * 50)
    print("搜索歌曲：Bohemian Rhapsody")
    print("=" * 50)
    
    results = await provider.search("Bohemian Rhapsody Queen", limit=5)
    
    for i, track in enumerate(results, 1):
        print(f"\n{i}. {track.artist} - {track.title}")
        print(f"   专辑：{track.album}")
        print(f"   时长：{track.duration // 60}:{track.duration % 60:02d}")
        print(f"   可用音质：{[q.value for q in track.quality_available]}")
        print(f"   预览：{track.extra.get('preview_url', 'N/A')[:50]}...")
    
    if not results:
        print("未找到结果")
        return
    
    # 使用第一个结果进行演示
    track = results[0]
    print(f"\n✓ 找到 {len(results)} 首歌曲")
    print()
    
    # ========== 获取流 URL ==========
    print("=" * 50)
    print("获取流 URL")
    print("=" * 50)
    
    try:
        # 尝试获取无损音质
        stream_url = await provider.get_stream_url(track.id, Quality.LOSSLESS)
        print(f"✓ 无损音质流 URL: {stream_url[:80]}...")
    except Exception as e:
        print(f"✗ 获取无损音质失败：{e}")
        print("  尝试获取高品质...")
        try:
            stream_url = await provider.get_stream_url(track.id, Quality.HIGH)
            print(f"✓ 高品质流 URL: {stream_url[:80]}...")
        except Exception as e2:
            print(f"✗ 获取高品质也失败：{e2}")
    
    print()
    
    # ========== 获取元数据 ==========
    print("=" * 50)
    print("获取元数据")
    print("=" * 50)
    
    try:
        metadata = await provider.get_metadata(track.id)
        print(f"✓ 元数据获取成功")
        print(f"  标题：{metadata.title}")
        print(f"  艺术家：{metadata.artist}")
        print(f"  专辑：{metadata.album}")
        print(f"  年份：{metadata.year}")
        print(f"  音轨号：{metadata.track_number}")
        print(f"  封面：{len(metadata.cover_data) if metadata.cover_data else 0} 字节")
        print(f"  歌词：{'有' if metadata.lyrics else '无'}")
    except Exception as e:
        print(f"✗ 获取元数据失败：{e}")
    
    print()
    
    # ========== 下载歌曲 ==========
    print("=" * 50)
    print("下载歌曲")
    print("=" * 50)
    
    download_dir = Path("./downloads/deezer")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 根据订阅类型选择合适的音质
        available_qualities = provider._get_available_qualities()
        best_quality = available_qualities[-1]  # 最高可用音质
        
        print(f"使用音质：{best_quality.value}")
        print(f"保存路径：{download_dir}")
        print("开始下载...")
        
        result = await provider.download(
            track_id=track.id,
            save_path=download_dir,
            quality=best_quality,
        )
        
        if result.success:
            print(f"✓ 下载成功!")
            print(f"  文件：{result.file_path}")
            print(f"  大小：{result.file_size / 1024 / 1024:.2f} MB")
            print(f"  音质：{result.quality.value}")
            if result.metadata:
                print(f"  元数据：已写入")
        else:
            print(f"✗ 下载失败：{result.error}")
            
    except Exception as e:
        print(f"✗ 下载异常：{e}")
    
    print()
    
    # ========== 获取专辑音轨 ==========
    print("=" * 50)
    print("获取专辑音轨")
    print("=" * 50)
    
    album_id = track.extra.get("album_id")
    if album_id:
        try:
            album_tracks = await provider.get_album_tracks(album_id)
            print(f"✓ 专辑包含 {len(album_tracks)} 首歌曲")
            for i, t in enumerate(album_tracks[:5], 1):
                print(f"  {i}. {t.title}")
            if len(album_tracks) > 5:
                print(f"  ... 还有 {len(album_tracks) - 5} 首")
        except Exception as e:
            print(f"✗ 获取专辑音轨失败：{e}")
    else:
        print("无法获取专辑 ID")
    
    print()
    
    # ========== 获取播放列表 ==========
    print("=" * 50)
    print("获取播放列表")
    print("=" * 50)
    
    # 示例播放列表 ID（可以替换为你自己的）
    playlist_id = "1362917935"  # Deezer 官方播放列表示例
    
    try:
        playlist_tracks = await provider.get_playlist(playlist_id)
        print(f"✓ 播放列表包含 {len(playlist_tracks)} 首歌曲")
        for i, t in enumerate(playlist_tracks[:5], 1):
            print(f"  {i}. {t.artist} - {t.title}")
        if len(playlist_tracks) > 5:
            print(f"  ... 还有 {len(playlist_tracks) - 5} 首")
    except Exception as e:
        print(f"✗ 获取播放列表失败：{e}")
    
    print()
    
    # 清理资源
    await provider.close()
    print("✓ Deezer 插件已关闭")


if __name__ == "__main__":
    asyncio.run(main())
