"""
Tests for Slidex configuration.
"""

import pytest
from pathlib import Path
from slidex.config import Settings


def test_settings_defaults():
    """Test that settings have expected defaults."""
    settings = Settings()
    
    assert settings.ollama_host == "http://localhost"
    assert settings.ollama_port == 11434
    assert settings.ollama_embedding_model == "nomic-embed-text"
    assert settings.ollama_summary_model == "granite4:tiny-h"
    assert settings.batch_size == 10
    assert settings.thumbnail_width == 320
    assert settings.top_k_results == 10


def test_settings_ollama_base_url():
    """Test ollama_base_url property."""
    settings = Settings()
    expected = f"{settings.ollama_host}:{settings.ollama_port}"
    assert settings.ollama_base_url == expected


def test_settings_paths():
    """Test that path properties work correctly."""
    settings = Settings()
    
    # Test directory properties
    assert settings.thumbnails_dir == settings.storage_root / "thumbnails"
    assert settings.slides_dir == settings.storage_root / "slides"
    assert settings.exports_dir == settings.storage_root / "exports"
    
    # Test that paths are Path objects
    assert isinstance(settings.storage_root, Path)
    assert isinstance(settings.faiss_index_path, Path)
    assert isinstance(settings.audit_db_path, Path)


def test_settings_ensure_directories(tmp_path):
    """Test that ensure_directories creates necessary directories."""
    # Use temporary directory for testing
    settings = Settings(storage_root=tmp_path / "test_storage")
    settings.ensure_directories()
    
    # Check that directories were created
    assert settings.storage_root.exists()
    assert settings.thumbnails_dir.exists()
    assert settings.slides_dir.exists()
    assert settings.exports_dir.exists()
    assert settings.faiss_index_path.parent.exists()
    assert settings.audit_db_path.parent.exists()
