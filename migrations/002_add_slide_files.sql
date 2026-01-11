-- Slidex Database Schema - Migration 002
-- Adds slide_file_path column to support individual slide files

-- Add slide_file_path column to slides table
ALTER TABLE slides ADD COLUMN IF NOT EXISTS slide_file_path TEXT;

-- Create index on slide_file_path for efficient lookups
CREATE INDEX IF NOT EXISTS idx_slides_slide_file_path ON slides(slide_file_path);

-- Add comment explaining the column
COMMENT ON COLUMN slides.slide_file_path IS 'Path to individual slide .pptx file for standalone access';
