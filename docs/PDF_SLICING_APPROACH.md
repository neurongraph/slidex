# PDF-Based Slicing Approach for Slidex

## Problem Statement

Current PPTX-based slicing (`save_slide_as_file`) has limitations with complex slides:

### Slide 9 Issues (CoreBankingNA.pptx)
- GroupShapes
- Tables
- Connectors
- **Lost 1 relationship during extraction**

### Slide 10 Issues (CoreBankingNA.pptx)
- **SmartArt diagrams** (most problematic)
- Multiple diagram parts: diagramData, diagramLayout, diagramColors, diagramQuickStyle, diagramDrawing
- **Lost 6 relationships during extraction** (all SmartArt parts)
- 15+ shapes with complex interconnections

### Root Cause
The `save_slide_as_file` method only copies `image` and `media` relationships. It does NOT copy:
- SmartArt diagram parts
- Chart data
- OLE object data  
- Custom XML parts
- Embedded fonts
- Audio/video media (partially)

## PDF-Based Solution

### Advantages
1. **100% Fidelity**: PDF preserves exact visual rendering
2. **No Relationship Dependencies**: Everything is flattened
3. **Universal Format**: Works with any PDF viewer
4. **Simpler Assembly**: Just concatenate PDFs
5. **Works with any content**: SmartArt, charts, animations (as images), embedded videos (as placeholders)

### Disadvantages
1. **No Editability**: Can't edit text/shapes in assembled output
2. **Larger File Sizes**: No compression/deduplication
3. **Loss of Animations**: Becomes static
4. **No Object Extraction**: Can't extract individual shapes

### Architecture

```
PowerPoint → PDF Conversion → Page Extraction → Storage → PDF Assembly
```

#### 1. PowerPoint to PDF Conversion
**Options:**
- **LibreOffice** (recommended): `soffice --headless --convert-to pdf --outdir /tmp file.pptx`
- **unoconv**: Python wrapper around LibreOffice
- **Microsoft PowerPoint** (Mac): Via AppleScript
- **PyMuPDF**: Can render PPTX via ghostscript

#### 2. PDF Page Extraction (Individual Slides)
**Tools:**
- **PyPDF2**: `PdfReader`, `PdfWriter`
- **pypdf**: Modern fork of PyPDF2
- **PyMuPDF (fitz)**: Faster, more features
- **PDFium**: Google's PDF library

**Example with pypdf:**
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("presentation.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"slide_{i}.pdf", "wb") as f:
        writer.write(f)
```

#### 3. PDF Assembly
**Simple concatenation:**
```python
from pypdf import PdfWriter

writer = PdfWriter()
for slide_id in selected_slides:
    slide_pdf = PdfReader(f"storage/slides_pdf/{slide_id}.pdf")
    writer.add_page(slide_pdf.pages[0])

writer.write("assembled.pdf")
```

### Hybrid Approach (Recommended)

Maintain BOTH formats:
1. **PPTX slices**: For simple slides without SmartArt/complex objects
2. **PDF slices**: As fallback/backup for all slides

**Decision Logic:**
- If slide has SmartArt → Use PDF
- If slide has lost relationships during PPTX extraction → Use PDF
- If user prefers editability → Use PPTX
- If user prefers fidelity → Use PDF

### Implementation Plan

#### Phase 1: PDF Extraction
1. Add PDF conversion to ingestion pipeline
2. Extract each slide as individual PDF
3. Store both PPTX and PDF versions
4. Add `slide_pdf_path` column to database

#### Phase 2: PDF Assembly
1. Create `PDFAssembler` class
2. Implement slide-to-PDF lookup
3. Add PDF assembly endpoint to API
4. Update UI to allow format selection

#### Phase 3: Hybrid Mode
1. Detect complex slides during ingestion
2. Flag slides that need PDF mode
3. Automatically choose best format during assembly
4. Allow manual override in UI

### Database Schema Changes

```sql
ALTER TABLE slides ADD COLUMN slide_pdf_path TEXT;
ALTER TABLE slides ADD COLUMN requires_pdf BOOLEAN DEFAULT FALSE;
ALTER TABLE slides ADD COLUMN complexity_score INTEGER DEFAULT 0;

-- Complexity scoring:
-- +10 for SmartArt
-- +5 for Charts
-- +3 for Tables
-- +2 for GroupShapes
-- +1 per OLE object
```

### Configuration

```python
# slidex/config.py
class Settings(BaseSettings):
    # PDF conversion
    libreoffice_path: str = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    pdf_conversion_enabled: bool = True
    pdf_dpi: int = 150  # Resolution for PDF rendering
    
    # Storage
    slides_pdf_dir: Path = Field(default_factory=lambda: Path("storage/slides_pdf"))
    
    # Assembly preferences
    prefer_pdf_for_smartart: bool = True
    prefer_pdf_for_charts: bool = False
    complexity_threshold_for_pdf: int = 15
```

### Migration Strategy

1. **Immediate**: Continue using PPTX for simple slides
2. **v1.1**: Add PDF extraction alongside PPTX (both stored)
3. **v1.2**: Add PDF assembly option
4. **v1.3**: Automatic format selection based on complexity
5. **v2.0**: Optional PPTX-only mode for lightweight deployments

### Testing

Test slides to verify:
- CoreBankingNA.pptx slides 9 & 10 (SmartArt)
- Slides with embedded Excel/Word objects
- Slides with custom animations
- Slides with audio/video
- Slides with complex tables
- Slides with grouped shapes

## Next Steps

1. ✅ Document current limitations
2. ⏭️ Implement PDF conversion in ingestion pipeline
3. ⏭️ Add PDF page extraction
4. ⏭️ Implement PDF assembly
5. ⏭️ Add complexity detection
6. ⏭️ Update UI for format selection
7. ⏭️ Test with problematic slides

## References

- **pypdf**: https://github.com/py-pdf/pypdf
- **PyMuPDF**: https://pymupdf.readthedocs.io/
- **LibreOffice headless**: https://help.libreoffice.org/Common/Starting_the_Software_With_Parameters
