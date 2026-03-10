"""
下载器插件基类
"""

from musichub.plugins.base import DownloaderPlugin
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import asyncio
import aiofiles


class HTTPDownloader(DownloaderPlugin):
    """
    HTTP 下载器实现
    
    支持：
    - 分块下载
    - 断点续传
    - 进度回调
    """
    
    name = "http"
    version = "1.0.0"
    description = "Standard HTTP/HTTPS downloader"
    supports_resume = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._session = None
    
    async def initialize(self) -> bool:
        """初始化下载器"""
        import httpx
        timeout = httpx.Timeout(
            timeout=self.config.get("timeout", 30.0),
            connect=10.0
        )
        limits = httpx.Limits(
            max_connections=self.config.get("max_connections", 100),
            max_keepalive_connections=self.config.get("max_keepalive", 20)
        )
        self._session = httpx.AsyncClient(timeout=timeout, limits=limits)
        self._initialized = True
        return True
    
    async def shutdown(self) -> None:
        """关闭下载器"""
        if self._session:
            await self._session.aclose()
            self._session = None
        self._initialized = False
    
    async def download(
        self,
        url: str,
        dest: Path,
        resume_data: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        下载文件
        
        Args:
            url: 下载 URL
            dest: 目标路径
            resume_data: 断点续传数据（包含 downloaded_bytes）
            progress_callback: 进度回调函数 (downloaded, total)
        
        Returns:
            下载结果字典
        """
        if not self._initialized:
            await self.initialize()
        
        headers = {}
        start_byte = 0
        
        # 处理断点续传
        if resume_data and "downloaded_bytes" in resume_data:
            start_byte = resume_data["downloaded_bytes"]
            headers["Range"] = f"bytes={start_byte}-"
        
        try:
            async with self._session.stream("GET", url, headers=headers) as response:
                if response.status_code not in (200, 206):
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "downloaded_bytes": 0,
                        "total_bytes": 0
                    }
                
                # 获取文件大小
                total_bytes = int(response.headers.get("content-length", 0)) + start_byte
                downloaded_bytes = start_byte
                chunk_size = self.config.get("chunk_size", 8192)
                
                # 确保目录存在
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                # 写入文件
                mode = "ab" if start_byte > 0 else "wb"
                async with aiofiles.open(dest, mode) as f:
                    async for chunk in response.aiter_bytes(chunk_size):
                        await f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        # 调用进度回调
                        if progress_callback:
                            progress_callback(downloaded_bytes, total_bytes)
                
                return {
                    "success": True,
                    "downloaded_bytes": downloaded_bytes,
                    "total_bytes": total_bytes,
                    "path": str(dest)
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "downloaded_bytes": downloaded_bytes,
                "total_bytes": 0
            }
