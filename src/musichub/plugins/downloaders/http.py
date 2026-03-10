"""
HTTP 下载器插件

标准 HTTP/HTTPS 文件下载实现
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import httpx

from musichub.plugins.downloaders.base import DownloaderPluginBase
from musichub.core.engine import DownloadResult
from musichub.plugins.base import PluginMetadata


class HTTPDownloader(DownloaderPluginBase):
    """
    HTTP 下载器
    
    支持：
    - 标准 HTTP/HTTPS 下载
    - 进度回调
    - 超时控制
    - 重试机制
    """
    
    metadata = PluginMetadata(
        name="http",
        version="0.1.0",
        description="标准 HTTP/HTTPS 下载器",
    )
    
    supports_resume = True
    
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
    
    async def initialize(self) -> None:
        """初始化 HTTP 客户端"""
        timeout = httpx.Timeout(
            timeout=self.config.get('timeout', 30.0),
            connect=10.0,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'MusicHub/0.1.0',
            },
        )
        await super().initialize()
    
    async def cleanup(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().cleanup()
    
    async def download(
        self,
        url: str,
        dest: Path,
        headers: dict[str, str] | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadResult:
        """
        下载文件
        
        Args:
            url: 下载 URL
            dest: 目标路径
            headers: 额外请求头
            progress_callback: 进度回调 (downloaded, total)
        
        Returns:
            下载结果
        """
        if not self._client:
            raise RuntimeError("下载器未初始化")
        
        start_time = time.time()
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # 合并请求头
        request_headers = {**(headers or {})}
        
        # 检查是否支持断点续传
        start_byte = 0
        if dest.exists() and self.supports_resume:
            start_byte = dest.stat().st_size
            request_headers['Range'] = f'bytes={start_byte}-'
        
        try:
            async with self._client.stream('GET', url, headers=request_headers) as response:
                if response.status_code not in (200, 206):
                    return DownloadResult(
                        success=False,
                        error=f"HTTP 错误：{response.status_code}",
                    )
                
                total = int(response.headers.get('content-length', 0)) or start_byte
                downloaded = start_byte
                
                mode = 'ab' if start_byte > 0 else 'wb'
                with open(dest, mode) as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total)
                
                elapsed = time.time() - start_time
                
                return DownloadResult(
                    success=True,
                    file_path=dest,
                    duration=elapsed,
                    size_bytes=downloaded,
                )
        
        except httpx.TimeoutException as e:
            return DownloadResult(
                success=False,
                error=f"下载超时：{e}",
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"下载失败：{e}",
            )
