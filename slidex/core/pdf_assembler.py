"""PDF assembler for creating presentations from selected slides."""

from pathlib import Path
from typing import List
from datetime import datetime

import fitz  # PyMuPDF

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import db


class PDFAssembler:
    """Assembles selected slides into a PDF presentation."""

    @staticmethod
    def assemble(
        slide_ids: List[str],
        output_filename: str | None = None,
        preserve_order: bool = False,
    ) -> Path:
        """Assemble slides into a PDF presentation.

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
        slides_data: list[dict] = []
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
                key=lambda x: (x["deck_path"], x["slide_index"]),
            )

        # Create output PDF document
        out_doc = fitz.open()

        # Add each slide's PDF page
        for slide_data in ordered_slides:
            pdf_path = slide_data.get("slide_pdf_path")

            if not pdf_path or not Path(pdf_path).exists():
                logger.warning(
                    f"PDF not found for slide {slide_data.get('slide_id')}, skipping"
                )
                continue

            try:
                src_doc = fitz.open(str(pdf_path))
                if src_doc.page_count > 0:
                    out_doc.insert_pdf(src_doc, from_page=0, to_page=0)
                    logger.debug(
                        "Added slide: %s",
                        slide_data.get("title_header") or "Untitled",
                    )
                src_doc.close()
            except Exception as e:  # pragma: no cover - defensive
                logger.error(
                    f"Error adding slide {slide_data.get('slide_id')} to PDF: {e}"
                )
                continue

        # Generate output filename
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"assembled_{timestamp}.pdf"

        # Save
        output_path = settings.exports_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        out_doc.save(str(output_path))
        page_count = out_doc.page_count
        out_doc.close()

        logger.info(f"PDF assembled: {output_path} ({page_count} pages)")
        return output_path


# Global instance
pdf_assembler = PDFAssembler()
