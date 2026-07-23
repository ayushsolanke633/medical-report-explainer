"""
utils/ocr.py
-------------
Extracts text from an uploaded medical report PDF.

Logic:
  1. Try pdfplumber first (fast, accurate for digitally-generated PDFs).
  2. If pdfplumber returns little/no text (common for scanned reports),
     fall back to rendering each page as an image with PyMuPDF and
     running pytesseract OCR on it.
  3. Merge all page text into a single string, preserving page breaks.
"""

import io
import logging

import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger("ocr")

# Minimum characters per page below which we consider pdfplumber's
# extraction "empty" and trigger the OCR fallback for that page.
MIN_CHARS_THRESHOLD = 20

# Rendering resolution for scanned pages (higher = better OCR, slower)
OCR_ZOOM = 2.0


class OCRError(Exception):
    """Raised when text cannot be extracted from the uploaded file."""
    pass


def _extract_with_pdfplumber(file_path: str) -> list[str]:
    """Returns a list of extracted text per page using pdfplumber."""
    pages_text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text.strip())
    return pages_text


def _extract_with_ocr(file_path: str, page_indices: list[int]) -> dict[int, str]:
    """
    Renders specific pages (by index) to images with PyMuPDF and runs
    pytesseract on each. Returns {page_index: extracted_text}.
    """
    ocr_results = {}
    doc = fitz.open(file_path)
    matrix = fitz.Matrix(OCR_ZOOM, OCR_ZOOM)

    try:
        for idx in page_indices:
            page = doc.load_page(idx)
            pix = page.get_pixmap(matrix=matrix)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image)
            ocr_results[idx] = text.strip()
    finally:
        doc.close()

    return ocr_results


def extract_text_from_pdf(file_path: str) -> str:
    """
    Main entry point. Extracts and merges text from every page of the
    given PDF, automatically choosing digital extraction or OCR per
    page as needed.

    Args:
        file_path: Absolute path to the saved PDF on disk.

    Returns:
        Merged text of the whole document, with page separators.

    Raises:
        OCRError: if no text could be extracted from any page.
    """
    try:
        pages_text = _extract_with_pdfplumber(file_path)
    except Exception as exc:
        logger.warning("pdfplumber failed (%s); falling back to full OCR", exc)
        pages_text = []

    # Determine which pages need OCR (empty or too short from pdfplumber)
    if not pages_text:
        with fitz.open(file_path) as doc:
            total_pages = doc.page_count
        pages_needing_ocr = list(range(total_pages))
        pages_text = [""] * total_pages
    else:
        pages_needing_ocr = [
            i for i, text in enumerate(pages_text) if len(text) < MIN_CHARS_THRESHOLD
        ]

    if pages_needing_ocr:
        logger.info("Running OCR fallback on %d page(s)", len(pages_needing_ocr))
        ocr_texts = _extract_with_ocr(file_path, pages_needing_ocr)
        for idx, text in ocr_texts.items():
            pages_text[idx] = text

    merged = "\n\n--- Page Break ---\n\n".join(
        text for text in pages_text if text
    )

    if not merged.strip():
        raise OCRError(
            "Could not extract any readable text from this PDF. "
            "The file may be corrupted, empty, or of very low image quality."
        )

    return merged
