"""
PDF processor for converting PowerPoint presentations to PDF
and extracting individual slides as separate PDF files.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image
import fitz  # PyMuPDF for all PDF operations (read/write/render)

from slidex.config import settings
from slidex.logging_config import logger


class PDFProcessor:
    """Handles PDF conversion and page extraction for PowerPoint slides."""
    
    @staticmethod
    def detect_libreoffice() -> Optional[Path]:
        """
        Detect LibreOffice installation.
        
        Returns:
            Path to LibreOffice executable if found, None otherwise
        """
        # Check configured path first
        configured_path = Path(settings.libreoffice_path)
        if configured_path.exists():
            return configured_path
        
        # Common LibreOffice paths on macOS
        mac_paths = [
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path("/usr/local/bin/soffice"),
        ]
        
        for path in mac_paths:
            if path.exists():
                logger.info(f"Found LibreOffice at: {path}")
                return path
        
        # Try to find in PATH
        soffice_path = shutil.which("soffice")
        if soffice_path:
            logger.info(f"Found LibreOffice in PATH: {soffice_path}")
            return Path(soffice_path)
        
        logger.warning("LibreOffice not found. PDF conversion will be disabled.")
        return None
    
    @staticmethod
    def convert_pptx_to_pdf(
        pptx_path: Path,
        output_dir: Optional[Path] = None,
        timeout: int = 60
    ) -> Optional[Path]:
        """
        Convert PowerPoint presentation to PDF using LibreOffice.
        
        Args:
            pptx_path: Path to the .pptx file
            output_dir: Directory to save the PDF (defaults to same as pptx)
            timeout: Command timeout in seconds
            
        Returns:
            Path to generated PDF file, or None if conversion failed
        """
        if not settings.pdf_conversion_enabled:
            logger.debug("PDF conversion is disabled in settings")
            return None
        
        soffice_path = PDFProcessor.detect_libreoffice()
        if not soffice_path:
            logger.error("LibreOffice not found, cannot convert to PDF")
            return None
        
        if not pptx_path.exists():
            logger.error(f"PPTX file not found: {pptx_path}")
            return None
        
        if output_dir is None:
            output_dir = pptx_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Expected output PDF path
        pdf_path = output_dir / f"{pptx_path.stem}.pdf"
        
        # Remove existing PDF if present
        if pdf_path.exists():
            pdf_path.unlink()
        
        logger.debug(f"Converting {pptx_path} to PDF using LibreOffice")
        
        try:
            # Run LibreOffice in headless mode
            result = subprocess.run(
                [
                    str(soffice_path),
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(output_dir),
                    str(pptx_path)
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                logger.error(f"LibreOffice conversion failed: {result.stderr}")
                return None
            
            if pdf_path.exists():
                logger.info(f"Successfully converted to PDF: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"PDF file was not created: {pdf_path}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"LibreOffice conversion timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error during PDF conversion: {e}")
            return None
    
    @staticmethod
    def extract_pdf_page(
        pdf_path: Path,
        page_index: int,
        output_path: Path
    ) -> bool:
        """
        Extract a single page from a PDF as a separate PDF file.
        
        Args:
            pdf_path: Path to the source PDF
            page_index: Index of the page to extract (0-based)
            output_path: Path where the single-page PDF should be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if not pdf_path.exists():
                logger.error(f"Source PDF not found for extraction: {pdf_path}")
                return False

            # Open source PDF and create a new single-page document
            src_doc = fitz.open(str(pdf_path))
            if page_index < 0 or page_index >= src_doc.page_count:
                logger.error(
                    f"Page index {page_index} out of range (total pages: {src_doc.page_count})"
                )
                return False

            out_doc = fitz.open()
            out_doc.insert_pdf(src_doc, from_page=page_index, to_page=page_index)
            out_doc.save(str(output_path))
            out_doc.close()
            src_doc.close()

            logger.debug(f"Extracted page {page_index} to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting PDF page {page_index}: {e}")
            return False
    
    @staticmethod
    def render_page_to_image(
        pdf_path: Path,
        page_index: int,
        width: int,
    ) -> Optional[Image.Image]:
        """Render a single PDF page to a Pillow image.

        Args:
            pdf_path: Path to the PDF file
            page_index: 0-based page index
            width: target width in pixels (height scaled proportionally)

        Returns:
            Pillow Image instance, or None on failure
        """
        try:
            if not pdf_path.exists():
                logger.error(f"PDF not found for thumbnail rendering: {pdf_path}")
                return None

            doc = fitz.open(str(pdf_path))
            if page_index < 0 or page_index >= doc.page_count:
                logger.error(
                    f"Thumbnail page index {page_index} out of range (pages: {doc.page_count})"
                )
                return None

            page = doc.load_page(page_index)
            # Compute zoom so that resulting image has roughly the requested width
            zoom = width / page.rect.width if page.rect.width else 1.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return img
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Error rendering PDF page {page_index} to image: {e}")
            return None

    @staticmethod
    def get_pdf_page_count(pdf_path: Path) -> int:
        """
        Get the number of pages in a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Number of pages, or 0 if error
        """
        try:
            if not pdf_path.exists():
                return 0
            doc = fitz.open(str(pdf_path))
            count = doc.page_count
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Error reading PDF page count: {e}")
            return 0


# Global PDF processor instance
pdf_processor = PDFProcessor()
