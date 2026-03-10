#!/usr/bin/env python3
"""
Apple Music 插件使用示例

演示如何使用 Apple Music 插件搜索和获取音乐信息
"""

import asyncio
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from musichub.providers import get_provider, list_providers
from musichub.providers.apple_music import AudioQuality, SpatialAudio


async def main():
    """主函数"""
    
    # 配置 Apple Music 插件
    config = {
        # 替换为你的实际 Token
        "api_token": "YOUR_API_TOKEN",
        "music_user_token": "YOUR_MUSIC_USER_TOKEN",
        
        # 区域设置
        "country": "US",
        "language": "en-US",
        
        # 音质设置
        "audio_quality": "lossless",
        "spatial_audio": "stereo",
        
        # 网络设置
        "timeout": 30,
        "max_retries": 3
    }
    
    # 创建插件实例
    provider = get_provider("apple_music", config)
    
    if not provider:
        print("❌ 无法创建 Apple Music 插件")
        return
    
    # 初始化插件
    print("🔄 初始化 Apple Music 插件...")
    success = await provider.initialize()
    
    if not success:
        print("❌ 插件初始化失败")
        return
    
    print("✅ 插件初始化成功")
    
    try:
        # 示例 1: 搜索歌曲
        print("\n🔍 搜索歌曲：Taylor Swift - Shake It Off")
        tracks = await provider.search("Shake It Off Taylor Swift", limit=5)
        
        for i, track in enumerate(tracks, 1):
            print(f"\n{i}. {track.title}")
            print(f"   艺术家：{track.artist}")
            print(f"   专辑：{track.album}")
            print(f"   时长：{track.duration}秒")
            print(f"   音质：{track.audio_quality.value}")
            if track.spatial_audio == SpatialAudio.DOLBY_ATMOS:
                print(f"   🎧 支持 Dolby Atmos")
        
        # 示例 2: 获取音轨详情
        if tracks:
            track_id = tracks[0].id
            print(f"\n📋 获取音轨详情 (ID: {track_id})")
            track_info = await provider.get_track_info(track_id)
            
            if track_info:
                print(f"   标题：{track_info.title}")
                print(f"   ISRC: {track_info.isrc}")
                print(f"   作曲：{track_info.composer}")
                print(f"   编码：{track_info.codec}")
                print(f"   比特率：{track_info.bitrate} kbps")
                print(f"   采样率：{track_info.sample_rate} Hz")
                print(f"   位深：{track_info.bit_depth} bit")
        
        # 示例 3: 搜索专辑
        print("\n💿 搜索专辑：1989")
        albums = await provider.search_albums("1989 Taylor Swift", limit=3)
        
        for i, album in enumerate(albums, 1):
            print(f"\n{i}. {album['name']}")
            print(f"   艺术家：{album['artist']}")
            print(f"   发行日期：{album['release_date']}")
            print(f"   音轨数：{album['track_count']}")
        
        # 示例 4: 获取专辑所有音轨
        if albums:
            album_id = albums[0]["id"]
            print(f"\n🎵 获取专辑音轨 (ID: {album_id})")
            album_tracks = await provider.get_album_tracks(album_id)
            print(f"   共 {len(album_tracks)} 首音轨")
            
            for i, track in enumerate(album_tracks[:5], 1):
                print(f"   {i}. {track.title} ({track.duration}秒)")
        
        # 示例 5: 搜索播放列表
        print("\n📝 搜索播放列表：Today's Hits")
        playlists = await provider.search_playlists("Today's Hits", limit=3)
        
        for i, playlist in enumerate(playlists, 1):
            print(f"\n{i}. {playlist['name']}")
            print(f"   编辑：{playlist['curator']}")
            print(f"   音轨数：{playlist['track_count']}")
        
        # 示例 6: 搜索艺术家
        print("\n🎤 搜索艺术家：Taylor Swift")
        artists = await provider.search_artists("Taylor Swift", limit=3)
        
        for i, artist in enumerate(artists, 1):
            print(f"\n{i}. {artist['name']}")
            print(f"   流派：{', '.join(artist['genre'])}")
            
            # 获取艺术家热门歌曲
            top_songs = await provider.get_artist_top_songs(artist["id"], limit=5)
            print(f"   热门歌曲:")
            for j, song in enumerate(top_songs[:3], 1):
                print(f"      {j}. {song.title}")
        
        # 示例 7: 获取流媒体 URL
        if tracks:
            track_id = tracks[0].id
            print(f"\n🔗 获取流媒体 URL (ID: {track_id})")
            
            # 标准音质
            stream_url = await provider.get_stream_url(
                track_id,
                quality=AudioQuality.STANDARD
            )
            if stream_url:
                print(f"   标准音质 URL: {stream_url[:50]}...")
            
            # 无损音质
            stream_url = await provider.get_stream_url(
                track_id,
                quality=AudioQuality.LOSSLESS
            )
            if stream_url:
                print(f"   无损音质 URL: {stream_url[:50]}...")
            
            # 高解析度音质
            stream_url = await provider.get_stream_url(
                track_id,
                quality=AudioQuality.HI_RES
            )
            if stream_url:
                print(f"   高解析度 URL: {stream_url[:50]}...")
        
        # 示例 8: 获取音质信息
        print("\n📊 音质信息:")
        for quality in AudioQuality:
            info = provider.get_quality_info(quality)
            print(f"\n   {quality.value.upper()}:")
            print(f"      编码：{info['codec']}")
            print(f"      比特率：{info['bitrate']} kbps")
            print(f"      采样率：{info['sample_rate']} Hz")
            print(f"      位深：{info['bit_depth']} bit")
            print(f"      描述：{info['description']}")
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        logging.exception("详细错误信息:")
    
    finally:
        # 关闭插件
        print("\n👋 关闭插件...")
        await provider.shutdown()
        print("✅ 插件已关闭")


if __name__ == "__main__":
    asyncio.run(main())
