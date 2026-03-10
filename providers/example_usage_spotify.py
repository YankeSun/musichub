"""
Spotify 插件使用示例

展示如何使用 SpotifyProvider 进行音乐搜索、下载和元数据获取。
"""

import asyncio
from pathlib import Path
from providers.spotify import SpotifyProvider, SpotifyConfig
from providers.base import Quality


async def main():
    # 配置 Spotify 插件
    # 注意：你需要从 Spotify Developer Dashboard 获取 client_id 和 client_secret
    # https://developer.spotify.com/dashboard
    config = {
        "client_id": "your_spotify_client_id",  # 替换为你的 Client ID
        "client_secret": "your_spotify_client_secret",  # 替换为你的 Client Secret
        "use_premium": False,  # 是否有 Premium 账号
        "timeout": 30,
        "retry_times": 3,
    }
    
    # 创建插件实例
    provider = SpotifyProvider(config)
    
    # 初始化插件
    success = await provider.initialize()
    if not success:
        print("插件初始化失败")
        return
    
    print("Spotify 插件初始化成功！\n")
    
    # ============== 示例 1: 搜索歌曲 ==============
    print("=" * 50)
    print("示例 1: 搜索歌曲")
    print("=" * 50)
    
    search_query = "Bohemian Rhapsody"
    print(f"搜索：{search_query}\n")
    
    try:
        results = await provider.search(search_query, limit=5)
        
        for i, track in enumerate(results, 1):
            print(f"{i}. {track.artist} - {track.title}")
            print(f"   专辑：{track.album}")
            print(f"   时长：{track.duration}秒")
            print(f"   音质：{[q.value for q in track.quality_available]}")
            print(f"   ID: {track.id}")
            print()
        
        if results:
            # 保存第一个结果的 ID 用于后续示例
            track_id = results[0].id
            print(f"使用歌曲 ID 进行后续操作：{track_id}\n")
        else:
            print("未找到搜索结果")
            return
            
    except Exception as e:
        print(f"搜索失败：{e}\n")
        return
    
    # ============== 示例 2: 获取歌曲元数据 ==============
    print("=" * 50)
    print("示例 2: 获取歌曲元数据")
    print("=" * 50)
    
    try:
        metadata = await provider.get_metadata(track_id)
        
        print(f"标题：{metadata.title}")
        print(f"艺术家：{metadata.artist}")
        print(f"专辑：{metadata.album}")
        print(f"曲目号：{metadata.track_number}")
        print(f"封面：{'有' if metadata.cover_data else '无'}")
        print(f"歌词：{'有' if metadata.lyrics else '无'}")
        print()
        
    except Exception as e:
        print(f"获取元数据失败：{e}\n")
    
    # ============== 示例 3: 获取流媒体 URL ==============
    print("=" * 50)
    print("示例 3: 获取流媒体 URL")
    print("=" * 50)
    
    try:
        stream_url = await provider.get_stream_url(track_id, quality=Quality.HIGH)
        print(f"流媒体 URL: {stream_url}")
        print(f"音质：HIGH (320kbps)")
        print()
        
    except Exception as e:
        print(f"获取流媒体 URL 失败：{e}\n")
    
    # ============== 示例 4: 下载歌曲 ==============
    print("=" * 50)
    print("示例 4: 下载歌曲")
    print("=" * 50)
    
    # 创建下载目录
    download_dir = Path("./downloads/spotify")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"下载目录：{download_dir}")
        print("开始下载...")
        
        result = await provider.download(
            track_id=track_id,
            save_path=download_dir,
            quality=Quality.HIGH,
        )
        
        if result.success:
            print(f"✓ 下载成功！")
            print(f"  文件路径：{result.file_path}")
            print(f"  文件大小：{result.file_size / 1024:.2f} KB")
            print(f"  音质：{result.quality.value}")
        else:
            print(f"✗ 下载失败：{result.error}")
        print()
        
    except Exception as e:
        print(f"下载异常：{e}\n")
    
    # ============== 示例 5: 获取歌单 ==============
    print("=" * 50)
    print("示例 5: 获取歌单歌曲列表")
    print("=" * 50)
    
    # 使用 Spotify 官方歌单示例 (Today's Top Hits)
    playlist_id = "37i9dQZF1DXcBWIGoYBM5M"
    print(f"歌单 ID: {playlist_id}\n")
    
    try:
        playlist_tracks = await provider.get_playlist(playlist_id)
        
        print(f"歌单包含 {len(playlist_tracks)} 首歌曲:")
        for i, track in enumerate(playlist_tracks[:10], 1):  # 只显示前 10 首
            print(f"  {i}. {track.artist} - {track.title}")
        
        if len(playlist_tracks) > 10:
            print(f"  ... 还有 {len(playlist_tracks) - 10} 首")
        print()
        
    except Exception as e:
        print(f"获取歌单失败：{e}\n")
    
    # ============== 示例 6: 解析 Spotify URL ==============
    print("=" * 50)
    print("示例 6: 解析 Spotify URL")
    print("=" * 50)
    
    test_urls = [
        "https://open.spotify.com/track/4u7EnebtmKWzUH433cf5Qv",
        "spotify:album:6akEvsycLGftJxYudPjmqK",
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
    ]
    
    for url in test_urls:
        parsed = provider.parse_spotify_url(url)
        if parsed:
            print(f"URL: {url}")
            print(f"  类型：{parsed['type']}")
            print(f"  ID: {parsed['id']}")
            print()
    
    # 关闭插件
    await provider.close()
    print("插件已关闭")


if __name__ == "__main__":
    # 运行示例
    # 注意：需要先将 client_id 和 client_secret 替换为有效的值
    print("Spotify 插件使用示例")
    print("警告：请将 config 中的 client_id 和 client_secret 替换为你的有效凭证\n")
    
    # asyncio.run(main())
    
    # 如果还没有配置凭证，显示提示信息
    print("=" * 50)
    print("配置指南")
    print("=" * 50)
    print("""
1. 访问 Spotify Developer Dashboard:
   https://developer.spotify.com/dashboard

2. 登录并创建一个新应用

3. 获取 Client ID 和 Client Secret

4. 在代码中替换以下配置:
   config = {
       "client_id": "your_spotify_client_id",
       "client_secret": "your_spotify_client_secret",
       "use_premium": False,
   }

5. 运行示例:
   python example_usage_spotify.py

注意:
- Spotify 不提供真正的无损音质
- 下载功能需要安装 spotDL: pip install spotdl
- Premium 账号可以获得更好的音质
""")
