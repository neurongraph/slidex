-- Slidex Database Schema - Consolidated Initialization Script
-- This script is idempotent and can be run multiple times safely
-- Combines migrations: 001_initial_schema.sql, 002_add_slide_files.sql, 003_add_pdf_support.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLES
-- ============================================================================

-- Decks table: stores metadata about PowerPoint files
CREATE TABLE IF NOT EXISTS decks (
    deck_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_hash TEXT NOT NULL UNIQUE,
    original_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    uploader TEXT,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    slide_count INTEGER NOT NULL DEFAULT 0,
    notes JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Slides table: stores metadata for individual slides
CREATE TABLE IF NOT EXISTS slides (
    slide_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(deck_id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,
    title_header TEXT,
    plain_text TEXT,
    summary_10_20_words TEXT,
    thumbnail_path TEXT,
    slide_file_path TEXT,
    slide_pdf_path TEXT,
    requires_pdf BOOLEAN DEFAULT FALSE,
    complexity_score INTEGER DEFAULT 0,
    original_slide_position INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(deck_id, slide_index)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Decks indexes
CREATE INDEX IF NOT EXISTS idx_decks_file_hash ON decks(file_hash);
CREATE INDEX IF NOT EXISTS idx_decks_uploaded_at ON decks(uploaded_at);

-- Slides indexes
CREATE INDEX IF NOT EXISTS idx_slides_deck_id ON slides(deck_id);
CREATE INDEX IF NOT EXISTS idx_slides_slide_index ON slides(slide_index);
CREATE INDEX IF NOT EXISTS idx_slides_slide_file_path ON slides(slide_file_path);
CREATE INDEX IF NOT EXISTS idx_slides_slide_pdf_path ON slides(slide_pdf_path);
CREATE INDEX IF NOT EXISTS idx_slides_requires_pdf ON slides(requires_pdf);
CREATE INDEX IF NOT EXISTS idx_slides_complexity_score ON slides(complexity_score);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to auto-update updated_at
DROP TRIGGER IF EXISTS update_decks_updated_at ON decks;
CREATE TRIGGER update_decks_updated_at BEFORE UPDATE ON decks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_slides_updated_at ON slides;
CREATE TRIGGER update_slides_updated_at BEFORE UPDATE ON slides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- USERS AND SESSIONS
-- ============================================================================

-- Users table: stores user identity from Google SSO
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    picture TEXT,
    google_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Sessions table: stores server-side session data
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    data JSONB DEFAULT '{}'::jsonb,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- USER/SESSION INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- ============================================================================
-- USER TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

-- Table comments
COMMENT ON TABLE decks IS 'Stores metadata about ingested PowerPoint files';
COMMENT ON TABLE slides IS 'Stores metadata for individual slides extracted from presentations';
COMMENT ON TABLE users IS 'Stores authenticated user information from Google SSO';
COMMENT ON TABLE sessions IS 'Stores active user sessions with server-side validation';

-- Column comments
COMMENT ON COLUMN slides.slide_file_path IS 'Path to individual slide .pptx file for standalone access';
COMMENT ON COLUMN slides.slide_pdf_path IS 'Path to individual slide PDF file for high-fidelity rendering';
COMMENT ON COLUMN slides.requires_pdf IS 'Flag indicating slide has complex content (SmartArt, etc.) requiring PDF format';
COMMENT ON COLUMN slides.complexity_score IS 'Calculated complexity score: +10 SmartArt, +5 Charts, +3 Tables, +2 Groups, +1 OLE/Connector';

-- Made with Bob
