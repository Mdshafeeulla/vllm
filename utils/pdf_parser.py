# utils/pdf_parser.py
import fitz  # PyMuPDF
from utils.logger import log

# Maximum pages to process to prevent CPU overload on huge PDFs
MAX_PAGES = 500


def extract_pdf_text(file_bytes: bytes, progress_callback=None) -> str:
    """
    Extract all text from a PDF given its raw bytes.
    If the PDF is a scanned image, falls back to OCR via EasyOCR.

    Args:
        file_bytes: Raw PDF bytes
        progress_callback: Optional callable(current_page, total_pages) for progress updates

    Returns extracted text as a single string.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = min(len(doc), MAX_PAGES)
    extracted_pages = []

    if len(doc) > MAX_PAGES:
        log.warning(
            f"[PDF] Document has {len(doc)} pages, processing only first {MAX_PAGES} "
            f"to prevent CPU overload."
        )

    for page_idx in range(total_pages):
        page = doc[page_idx]
        text = page.get_text("text").strip()

        if text:
            extracted_pages.append(text)
        else:
            # Fallback: render page to image for scanned PDF OCR
            # Use lower DPI (100) to reduce CPU/memory usage
            try:
                pix = page.get_pixmap(dpi=100)
                img_bytes = pix.tobytes("png")
                from utils.image_parser import extract_image_text
                ocr_text = extract_image_text(img_bytes)
                if ocr_text:
                    extracted_pages.append(ocr_text)
            except Exception as e:
                log.warning(f"[PDF] OCR failed for page {page_idx + 1}: {e}")

        # Report progress if callback provided
        if progress_callback:
            try:
                progress_callback(page_idx + 1, total_pages)
            except Exception:
                pass

    doc.close()

    full_text = "\n".join(extracted_pages).strip()
    log.info(
        f"[PDF] Extracted {len(full_text)} chars from {total_pages} pages "
        f"({len(extracted_pages)} pages had text)"
    )
    return full_text
