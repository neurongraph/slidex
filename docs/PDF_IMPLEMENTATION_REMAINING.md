# Remaining Implementation Steps for Hybrid PDF Approach

## Completed ✅
1. Database migration (003_add_pdf_support.sql)
2. Configuration settings (slidex/config.py)
3. PDF processor module (slidex/core/pdf_processor.py)
4. pypdf dependency added

## Step 5: Update Database Module

File: `slidex/core/database.py`

Update `insert_slide_with_id` method:
```python
@staticmethod
def insert_slide_with_id(
    slide_id: str,
    deck_id: str,
    slide_index: int,
    title_header: Optional[str],
    plain_text: str,
    summary: str,
    thumbnail_path: str,
    original_slide_position: int,
    slide_file_path: Optional[str] = None,
    slide_pdf_path: Optional[str] = None,  # NEW
    requires_pdf: bool = False,  # NEW
    complexity_score: int = 0,  # NEW
) -> None:
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            INSERT INTO slides 
            (slide_id, deck_id, slide_index, title_header, plain_text, 
             summary_10_20_words, thumbnail_path, original_slide_position, 
             slide_file_path, slide_pdf_path, requires_pdf, complexity_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING slide_id
            """,
            (slide_id, deck_id, slide_index, title_header, plain_text,
             summary, thumbnail_path, original_slide_position, slide_file_path,
             slide_pdf_path, requires_pdf, complexity_score)
        )
```

## Step 6: Add Complexity Detection

File: `slidex/core/slide_processor.py`

Add methods:
```python
@staticmethod
def calculate_complexity_score(slide, presentation) -> int:
    """
    Calculate complexity score for a slide.
    Scoring:
    - +10 for SmartArt (diagram relationships)
    - +5 for Charts
    - +3 for Tables
    - +2 for GroupShapes
    - +1 per OLE object
    - +1 per Connector
    """
    score = 0
    
    # Check relationships for SmartArt
    if hasattr(slide, 'part') and hasattr(slide.part, 'rels'):
        for rel_id, rel in slide.part.rels.items():
            reltype_lower = rel.reltype.lower()
            if 'diagram' in reltype_lower:
                score += 10
                break  # Only count once per slide
    
    # Check shapes
    for shape in slide.shapes:
        shape_type = type(shape).__name__
        
        if shape_type == 'GraphicFrame':
            # Could be table or chart
            try:
                if hasattr(shape, 'has_table') and shape.has_table:
                    score += 3
                elif hasattr(shape, 'has_chart') and shape.has_chart:
                    score += 5
            except:
                pass
        elif shape_type == 'GroupShape':
            score += 2
        elif shape_type == 'Connector':
            score += 1
        
        # Check for OLE objects
        if hasattr(shape, 'shape_type'):
            if 'OLE' in str(shape.shape_type):
                score += 1
    
    return score

@staticmethod
def requires_pdf_format(complexity_score: int) -> bool:
    """Determine if slide requires PDF format based on complexity."""
    return complexity_score >= settings.complexity_threshold_for_pdf
```

## Step 7: Update Ingestion

File: `slidex/core/ingest.py`

In `ingest_file` method, after processing each slide:

```python
# After generating thumbnail and summary...

# Calculate complexity score
complexity_score = slide_processor.calculate_complexity_score(slide, presentation)
requires_pdf = slide_processor.requires_pdf_format(complexity_score)

logger.debug(f"Slide {slide_idx} complexity: {complexity_score}, requires_pdf: {requires_pdf}")

# Store paths for later (after all slides processed)
slide_data_for_pdf.append({
    'slide_id': slide_id,
    'slide_idx': slide_idx,
    'complexity_score': complexity_score,
    'requires_pdf': requires_pdf
})
```

After processing all slides:

```python
# Convert entire deck to PDF
pdf_path = None
if settings.pdf_conversion_enabled:
    try:
        pdf_path = pdf_processor.convert_pptx_to_pdf(file_path)
        if pdf_path:
            # Extract individual PDF pages
            for data in slide_data_for_pdf:
                slide_id = data['slide_id']
                slide_idx = data['slide_idx']
                
                pdf_output_path = settings.slides_pdf_dir / f"{slide_id}.pdf"
                success = pdf_processor.extract_pdf_page(pdf_path, slide_idx, pdf_output_path)
                
                if success:
                    data['slide_pdf_path'] = str(pdf_output_path)
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")

# Update database records with PDF paths and complexity scores
for data in slide_data_for_pdf:
    db.insert_slide_with_id(
        slide_id=data['slide_id'],
        # ... other params ...
        slide_pdf_path=data.get('slide_pdf_path'),
        requires_pdf=data['requires_pdf'],
        complexity_score=data['complexity_score']
    )
```

## Step 8: Create PDF Assembler

File: `slidex/core/pdf_assembler.py`

```python
"""PDF assembler for creating presentations from selected slides."""

from pathlib import Path
from typing import List
from datetime import datetime
from pypdf import PdfWriter, PdfReader

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import db


class PDFAssembler:
    """Assembles selected slides into a PDF presentation."""
    
    @staticmethod
    def assemble(
        slide_ids: List[str],
        output_filename: str = None,
        preserve_order: bool = False
    ) -> Path:
        """
        Assemble slides into a PDF presentation.
        
        Args:
            slide_ids: List of slide IDs
            output_filename: Optional output filename
            preserve_order: Whether to preserve slide ID order
            
        Returns:
            Path to assembled PDF
        """
        if not slide_ids:
            raise ValueError("No slides provided")
        
        logger.info(f"Assembling PDF with {len(slide_ids)} slides")
        
        # Fetch slide metadata
        slides_data = []
        for slide_id in slide_ids:
            slide = db.get_slide_by_id(slide_id)
            if not slide:
                logger.warning(f"Slide not found: {slide_id}")
                continue
            slides_data.append(slide)
        
        if not slides_data:
            raise ValueError("No valid slides found")
        
        # Order slides
        if preserve_order:
            ordered_slides = slides_data
        else:
            ordered_slides = sorted(
                slides_data,
                key=lambda x: (x['deck_path'], x['slide_index'])
            )
        
        # Create PDF writer
        writer = PdfWriter()
        
        # Add each slide's PDF page
        for slide_data in ordered_slides:
            pdf_path = slide_data.get('slide_pdf_path')
            
            if not pdf_path or not Path(pdf_path).exists():
                logger.warning(f"PDF not found for slide {slide_data['slide_id']}, skipping")
                continue
            
            try:
                reader = PdfReader(str(pdf_path))
                if len(reader.pages) > 0:
                    writer.add_page(reader.pages[0])
                    logger.debug(f"Added slide: {slide_data.get('title_header') or 'Untitled'}")
            except Exception as e:
                logger.error(f"Error adding slide {slide_data['slide_id']}: {e}")
                continue
        
        # Generate output filename
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"assembled_{timestamp}.pdf"
        
        # Save
        output_path = settings.exports_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        logger.info(f"PDF assembled: {output_path} ({len(writer.pages)} pages)")
        return output_path


# Global instance
pdf_assembler = PDFAssembler()
```

## Step 9: Update Main Assembler

File: `slidex/core/assembler.py`

Add format parameter to `assemble` method:

```python
@staticmethod
def assemble(
    slide_ids: List[str],
    output_filename: Optional[str] = None,
    preserve_order: bool = False,
    output_format: str = 'pptx'  # NEW: 'pptx' or 'pdf'
) -> Path:
    """Assemble slides into presentation."""
    
    if output_format == 'pdf':
        from slidex.core.pdf_assembler import pdf_assembler
        return pdf_assembler.assemble(slide_ids, output_filename, preserve_order)
    
    # Existing PPTX assembly code...
```

## Step 10: Update API

File: `slidex/api/app.py`

Update `/api/assemble` endpoint:

```python
@app.route('/api/assemble', methods=['POST'])
def assemble_slides():
    data = request.json
    slide_ids = data.get('slide_ids', [])
    preserve_order = data.get('preserve_order', True)
    output_format = data.get('output_format', 'pptx')  # NEW
    
    # ... validation ...
    
    output_path = slide_assembler.assemble(
        slide_ids, 
        preserve_order=preserve_order,
        output_format=output_format  # NEW
    )
    
    # Set appropriate content type
    if output_format == 'pdf':
        content_type = 'application/pdf'
    else:
        content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    
    # Return download URL
    download_url = f'/api/download/{output_path.name}?format={output_format}'
    
    return jsonify({
        'success': True,
        'output_path': str(output_path),
        'download_url': download_url,
        'format': output_format
    })
```

## Step 11: Update UI

File: `slidex/templates/index.html`

Add format selector before assemble button:

```html
<div class="assemble-section" id="assembleSection">
    <div class="container">
        <span id="selectedCount">0 slides selected</span>
        
        <!-- NEW: Format selector -->
        <div class="format-selector">
            <label>
                <input type="radio" name="outputFormat" value="pptx" checked>
                PowerPoint (Editable)
            </label>
            <label>
                <input type="radio" name="outputFormat" value="pdf">
                PDF (High Fidelity)
            </label>
            <label>
                <input type="radio" name="outputFormat" value="auto">
                Auto (Best for each slide)
            </label>
        </div>
        
        <button onclick="assembleSlides()">Assemble Presentation</button>
    </div>
</div>
```

Update `assembleSlides()` function:

```javascript
async function assembleSlides() {
    if (selectedSlides.size === 0) return;
    
    const format = document.querySelector('input[name="outputFormat"]:checked').value;
    
    try {
        const response = await fetch('/api/assemble', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                slide_ids: Array.from(selectedSlides),
                preserve_order: true,
                output_format: format  // NEW
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`${data.format.toUpperCase()} assembled successfully!`);
            window.location.href = data.download_url;
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}
```

## Step 12: Run Migration

```bash
psql postgresql://localhost:5432/slidex -f migrations/003_add_pdf_support.sql
```

## Testing

1. Test PDF conversion:
```bash
uv run python -c "from slidex.core.pdf_processor import pdf_processor; print(pdf_processor.detect_libreoffice())"
```

2. Ingest CoreBankingNA.pptx:
```bash
just ingest-file tests/test_ppts/CoreBankingNA.pptx
```

3. Search and assemble with PDF format

4. Verify slides 9 & 10 work correctly

## Notes

- **Auto format**: Requires logic to check `requires_pdf` flag per slide and create hybrid assembly
- **Complexity badges**: Add visual indicators in UI for slides requiring PDF
- **Backward compatibility**: Existing slides without PDF will still work with PPTX-only mode
