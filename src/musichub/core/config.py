"""
配置管理 - 使用 Pydantic 进行配置验证和管理
"""

from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DownloadConfig(BaseModel):
    """下载配置"""
    max_concurrent_downloads: int = Field(default=5, ge=1, le=20)
    chunk_size: int = Field(default=8192, ge=1024)
    timeout: int = Field(default=30, ge=5)
    max_retries: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0)
    enable_resume: bool = True


class ExportConfig(BaseModel):
    """导出配置"""
    default_format: str = Field(default="mp3")
    output_directory: Path = Field(default_factory=lambda: Path("./downloads"))
    write_metadata: bool = True
    embed_cover_art: bool = True
    audio_quality: str = Field(default="320k")  # 对于 MP3: 128k, 192k, 320k; 对于 FLAC: 默认
    
    @field_validator('default_format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """验证音频格式"""
        valid_formats = ["mp3", "flac", "m4a", "wav", "ogg"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid format: {v}. Must be one of {valid_formats}")
        return v.lower()
    
    @field_validator('audio_quality')
    @classmethod
    def validate_quality(cls, v: str) -> str:
        """验证音频质量"""
        valid_qualities = ["128k", "192k", "256k", "320k", "lossless"]
        if v.lower() not in valid_qualities:
            raise ValueError(f"Invalid quality: {v}. Must be one of {valid_qualities}")
        return v.lower()


class SourceConfig(BaseModel):
    """音源配置"""
    enabled_sources: list[str] = Field(default_factory=lambda: ["netease", "qqmusic"])
    api_keys: Dict[str, str] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class Config(BaseSettings):
    """
    全局配置类
    
    支持从环境变量和配置文件加载
    """
    
    model_config = SettingsConfigDict(
        env_prefix="MUSICHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # 应用配置
    app_name: str = "MusicHub"
    version: str = "0.1.0"
    debug: bool = False
    
    # 下载配置
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    
    # 导出配置
    export: ExportConfig = Field(default_factory=ExportConfig)
    
    # 音源配置
    sources: SourceConfig = Field(default_factory=SourceConfig)
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    # 验证器已移至对应的子配置类中
    
    def ensure_directories(self) -> None:
        """确保所有必要的目录存在"""
        self.export.output_directory.mkdir(parents=True, exist_ok=True)
        
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """从文件加载配置"""
        if config_path and config_path.exists():
            # 可以从 YAML/JSON 文件加载额外配置
            pass
        return cls()
    
    def save(self, config_path: Path) -> None:
        """保存配置到文件"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            f.write(self.model_dump_json(indent=2))
