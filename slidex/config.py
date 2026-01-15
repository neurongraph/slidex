"""
Slidex central configuration using Pydantic.
All settings can be overridden via environment variables or config/dev.yaml
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Slidex application."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Database
    database_url: str = Field(
        default="postgresql://localhost:5432/slidex",
        description="PostgreSQL connection URL"
    )
    
    # Ollama configuration
    ollama_host: str = Field(default="http://localhost", description="Ollama host URL")
    ollama_port: int = Field(default=11434, description="Ollama port")
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name"
    )
    ollama_summary_model: str = Field(
        default="granite4:tiny-h",
        description="Ollama LLM model for summarization"
    )
    
    # Storage paths
    storage_root: Path = Field(
        default=Path("storage"),
        description="Base storage directory"
    )
    faiss_index_path: Path = Field(
        default=Path("storage/faiss_index.bin"),
        description="FAISS index file path"
    )
    audit_db_path: Path = Field(
        default=Path("storage/audit.db"),
        description="SQLite audit log database path"
    )
    
    # LightRAG configuration
    lightrag_working_dir: Path = Field(
        default=Path("storage/lightrag"),
        description="LightRAG working directory for graph storage"
    )
    lightrag_enabled: bool = Field(
        default=True,
        description="Enable LightRAG for indexing and search"
    )
    lightrag_llm_context_size: int = Field(
        default=32768,
        description="Context size for LightRAG LLM (minimum 32k recommended)"
    )
    
    # PDF configuration
    pdf_conversion_enabled: bool = Field(
        default=True,
        description="Enable PDF conversion for complex slides"
    )
    libreoffice_path: str = Field(
        default="/Applications/LibreOffice.app/Contents/MacOS/soffice",
        description="Path to LibreOffice executable for PDF conversion"
    )
    pdf_dpi: int = Field(
        default=150,
        description="DPI for PDF rendering (higher = better quality, larger file)"
    )
    complexity_threshold_for_pdf: int = Field(
        default=10,
        description="Complexity score threshold for requiring PDF format"
    )
    prefer_pdf_for_smartart: bool = Field(
        default=True,
        description="Automatically use PDF format for slides with SmartArt"
    )
    
    # Processing configuration
    batch_size: int = Field(default=10, description="Batch size for processing")
    thumbnail_width: int = Field(default=320, description="Thumbnail width in pixels")
    top_k_results: int = Field(default=10, description="Default number of search results")
    
    # Logging
    log_level: str = Field(default="DEBUG", description="Logging level")
    
    # Flask
    flask_host: str = Field(default="0.0.0.0", description="Flask host")
    flask_port: int = Field(default=5000, description="Flask port")
    flask_debug: bool = Field(default=True, description="Flask debug mode")
    
    @property
    def ollama_base_url(self) -> str:
        """Full Ollama base URL."""
        return f"{self.ollama_host}:{self.ollama_port}"
    
    @property
    def thumbnails_dir(self) -> Path:
        """Thumbnails storage directory."""
        return self.storage_root / "thumbnails"
    
    @property
    def slides_dir(self) -> Path:
        """Individual slides storage directory (PPTX)."""
        return self.storage_root / "slides"
    
    @property
    def slides_pdf_dir(self) -> Path:
        """Individual slides PDF storage directory."""
        return self.storage_root / "slides_pdf"
    
    @property
    def exports_dir(self) -> Path:
        """Exports storage directory."""
        return self.storage_root / "exports"
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.slides_dir.mkdir(parents=True, exist_ok=True)
        if self.pdf_conversion_enabled:
            self.slides_pdf_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lightrag_enabled:
            self.lightrag_working_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()
