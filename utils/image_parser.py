# utils/image_parser.py
import easyocr
import numpy as np
from PIL import Image
import io
import torch
from utils.logger import log

_reader = None

def _get_reader():
    global _reader
    if _reader is None:
        use_gpu = torch.cuda.is_available()
        log.info(f"[OCR] Initializing EasyOCR reader (GPU={use_gpu})...")
        _reader = easyocr.Reader(['en'], gpu=use_gpu)
        log.info("[OCR] EasyOCR initialized successfully ✓")
    return _reader


def extract_image_text(file_bytes: bytes) -> str:
    """
    Extract text from raw image bytes (PNG, JPG, JPEG, WEBP, BMP) using EasyOCR.
    Returns extracted text as string.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img_np = np.array(image)
        reader = _get_reader()
        results = reader.readtext(img_np, detail=0)
        extracted = "\n".join(results).strip()
        log.info(f"[OCR] Extracted {len(extracted)} chars from image")
        return extracted
    except Exception as e:
        log.error(f"[OCR] Failed to extract text from image: {e}")
        return ""
