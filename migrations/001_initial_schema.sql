-- Slidex Database Schema - Initial Migration
-- Creates tables for decks and slides

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

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
    original_slide_position INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(deck_id, slide_index)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_decks_file_hash ON decks(file_hash);
CREATE INDEX IF NOT EXISTS idx_decks_uploaded_at ON decks(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_slides_deck_id ON slides(deck_id);
CREATE INDEX IF NOT EXISTS idx_slides_slide_index ON slides(slide_index);

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
