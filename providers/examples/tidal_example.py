#!/usr/bin/env python3
"""
Tidal 插件使用示例

演示如何使用 TidalProvider 搜索、下载和管理音乐。

依赖:
- httpx
- mutagen (用于元数据写入)

运行前请确保已安装依赖:
    pip install httpx mutagen
"""

import asyncio
from pathlib import Path
from providers import create_provider, Quality


async def main():
    # Tidal 配置
    config = {
        # 方式 1: 使用 API Token (如果你有)
        # "api_token": "your_tidal_api_token",
        
        # 方式 2: 使用客户端凭证 (默认已配置)
        # "client_id": "km8T9pS355y7dd",
        # "client_secret": "66k2C6IZmV7cbrQUN99VqKzrN5WQ33J2oZ7Cz2b5sNA=",
        
        # 音质设置
        "quality": "LOSSLESS",  # 或 "HI_RES" (需要 HiFi Plus 订阅)
        
        # 其他配置
        "timeout": 30,
        "retry_times": 3,
        "country_code": "US",
    }
    
    # 创建并初始化插件
    tidal = await create_provider("tidal", config)
    
    try:
        # ========== 搜索歌曲 ==========
        print("搜索歌曲：Bohemian Rhapsody")
        results = await tidal.search("Bohemian Rhapsody", limit=5)
        
        print(f"找到 {len(results)} 首歌曲:\n")
        for i, track in enumerate(results, 1):
            print(f"{i}. {track.artist} - {track.title}")
            print(f"   专辑：{track.album}")
            print(f"   时长：{track.duration}s")
            print(f"   可用音质：{[q.value for q in track.quality_available]}")
            print()
        
        if not results:
            print("未找到歌曲")
            return
        
        # ========== 下载歌曲 ==========
        track = results[0]
        print(f"\n下载歌曲：{track.artist} - {track.title}")
        
        download_dir = Path("./downloads/tidal")
        result = await tidal.download(
            track_id=track.id,
            save_path=download_dir,
            quality=Quality.LOSSLESS,  # 尝试下载无损音质
        )
        
        if result.success:
            print(f"✓ 下载完成：{result.file_path}")
            print(f"  文件大小：{result.file_size / 1024 / 1024:.2f} MB")
            print(f"  音质：{result.quality.value}")
        else:
            print(f"✗ 下载失败：{result.error}")
        
        # ========== 获取元数据 ==========
        print("\n获取元数据...")
        metadata = await tidal.get_metadata(track.id)
        print(f"  标题：{metadata.title}")
        print(f"  艺术家：{metadata.artist}")
        print(f"  专辑：{metadata.album}")
        print(f"  年份：{metadata.year}")
        print(f"  音轨号：{metadata.track_number}")
        if metadata.cover_data:
            print(f"  封面：{len(metadata.cover_data)} bytes")
        
        # ========== 获取专辑音轨 ==========
        album_id = track.extra.get("album_id")
        if album_id:
            print(f"\n获取专辑音轨 (专辑 ID: {album_id})...")
            album_tracks = await tidal.get_album_tracks(album_id)
            print(f"专辑包含 {len(album_tracks)} 首歌曲:")
            for i, t in enumerate(album_tracks[:5], 1):
                print(f"  {i}. {t.title}")
        
        # ========== 获取播放列表 ==========
        # 示例播放列表 ID (需要替换为实际的播放列表 ID)
        # playlist_id = "your_playlist_id"
        # print(f"\n获取播放列表...")
        # playlist_tracks = await tidal.get_playlist(playlist_id)
        # print(f"播放列表包含 {len(playlist_tracks)} 首歌曲")
        
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭插件
        await tidal.close()
        print("\n插件已关闭")


if __name__ == "__main__":
    asyncio.run(main())
