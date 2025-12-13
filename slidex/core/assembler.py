"""
Slide assembler for creating new PowerPoint presentations from selected slides.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches
import shutil
from copy import deepcopy

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import db


class SlideAssembler:
    """Assembles selected slides into a new PowerPoint presentation."""
    
    @staticmethod
    def assemble(
        slide_ids: List[str],
        output_filename: Optional[str] = None,
        preserve_order: bool = False
    ) -> Path:
        """
        Assemble slides into a new presentation.
        
        Args:
            slide_ids: List of slide IDs to include
            output_filename: Optional output filename (generated if not provided)
            preserve_order: If True, preserve the order of slide_ids; 
                          otherwise order by original deck order
            
        Returns:
            Path to the generated presentation file
        """
        if not slide_ids:
            raise ValueError("No slides provided for assembly")
        
        logger.info(f"Assembling presentation with {len(slide_ids)} slides")
        
        # Fetch slide metadata
        slides_data = []
        for slide_id in slide_ids:
            slide = db.get_slide_by_id(slide_id)
            if not slide:
                logger.warning(f"Slide not found: {slide_id}, skipping")
                continue
            slides_data.append(slide)
        
        if not slides_data:
            raise ValueError("No valid slides found")
        
        # Group slides by deck to efficiently load presentations
        slides_by_deck = {}
        for slide_data in slides_data:
            deck_path = slide_data['deck_path']
            if deck_path not in slides_by_deck:
                slides_by_deck[deck_path] = []
            slides_by_deck[deck_path].append(slide_data)
        
        # Create new presentation
        new_prs = Presentation()
        
        # For proper sizing, we can set the slide dimensions from the first source
        # or use default dimensions
        
        # Process slides in the requested order
        if preserve_order:
            ordered_slides = slides_data
        else:
            # Order by deck path and then slide index
            ordered_slides = sorted(
                slides_data,
                key=lambda x: (x['deck_path'], x['slide_index'])
            )
        
        # Track which decks we've already loaded
        loaded_decks = {}
        
        for slide_data in ordered_slides:
            deck_path = slide_data['deck_path']
            slide_index = slide_data['slide_index']
            
            try:
                # Load source presentation if not already loaded
                if deck_path not in loaded_decks:
                    source_prs = Presentation(deck_path)
                    loaded_decks[deck_path] = source_prs
                    logger.debug(f"Loaded source presentation: {deck_path}")
                else:
                    source_prs = loaded_decks[deck_path]
                
                # Get the source slide
                source_slide = source_prs.slides[slide_index]
                
                # Copy slide to new presentation
                SlideAssembler._copy_slide(source_slide, new_prs)
                
                logger.debug(
                    f"Copied slide: {slide_data['title_header'] or f'Slide {slide_index}'}"
                )
                
            except Exception as e:
                logger.error(
                    f"Error copying slide {slide_index} from {deck_path}: {e}"
                )
                # Continue with other slides
                continue
        
        # Generate output filename if not provided
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"assembled_{timestamp}.pptx"
        
        # Ensure output directory exists
        output_path = settings.exports_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save new presentation
        new_prs.save(str(output_path))
        
        logger.info(f"Presentation assembled: {output_path} ({len(new_prs.slides)} slides)")
        
        return output_path
    
    @staticmethod
    def _copy_slide(source_slide, target_presentation: Presentation) -> None:
        """
        Copy a slide from source to target presentation using deep XML cloning.
        This preserves all formatting, shapes, images, and content.
        """
        # Copy slide dimensions if this is the first slide
        if len(target_presentation.slides) == 0:
            # Get dimensions from the source presentation
            src_prs = source_slide.part.package.presentation_part.presentation
            target_presentation.slide_width = src_prs.slide_width
            target_presentation.slide_height = src_prs.slide_height
        
        # Get a blank slide layout from target
        blank_layout = target_presentation.slide_layouts[6]
        
        # Add new slide with blank layout
        new_slide = target_presentation.slides.add_slide(blank_layout)
        
        # Deep copy the entire slide XML tree from source to target
        # This preserves all content, formatting, and relationships
        for shape in source_slide.shapes:
            # Clone the shape's XML element
            el = shape.element
            newel = deepcopy(el)
            new_slide.shapes._spTree.insert_element_before(newel, 'p:extLst')
        
        # Copy image and media relationships
        try:
            for rel in source_slide.part.rels.values():
                # Copy image and other media relationships
                if 'image' in rel.reltype or 'media' in rel.reltype:
                    try:
                        # Get the related part
                        related_part = rel.target_part
                        # Create equivalent relationship in new slide
                        new_slide.part.relate_to(related_part, rel.reltype)
                    except Exception as e:
                        logger.debug(f"Could not copy relationship: {e}")
        except Exception as e:
            logger.debug(f"Error copying slide relationships: {e}")
    


# Global assembler instance
slide_assembler = SlideAssembler()
