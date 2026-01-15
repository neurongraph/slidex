-- Slidex Database Schema - Migration 003
-- Adds PDF support for hybrid PPTX+PDF slicing

-- Add PDF file path column
ALTER TABLE slides ADD COLUMN IF NOT EXISTS slide_pdf_path TEXT;

-- Add flag indicating if slide requires PDF format (complex content)
ALTER TABLE slides ADD COLUMN IF NOT EXISTS requires_pdf BOOLEAN DEFAULT FALSE;

-- Add complexity score for determining PDF requirement
ALTER TABLE slides ADD COLUMN IF NOT EXISTS complexity_score INTEGER DEFAULT 0;

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_slides_slide_pdf_path ON slides(slide_pdf_path);
CREATE INDEX IF NOT EXISTS idx_slides_requires_pdf ON slides(requires_pdf);
CREATE INDEX IF NOT EXISTS idx_slides_complexity_score ON slides(complexity_score);

-- Add comments explaining the columns
COMMENT ON COLUMN slides.slide_pdf_path IS 'Path to individual slide PDF file for high-fidelity rendering';
COMMENT ON COLUMN slides.requires_pdf IS 'Flag indicating slide has complex content (SmartArt, etc.) requiring PDF format';
COMMENT ON COLUMN slides.complexity_score IS 'Calculated complexity score: +10 SmartArt, +5 Charts, +3 Tables, +2 Groups, +1 OLE/Connector';
