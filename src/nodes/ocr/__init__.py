from pathlib import Path

from .docx import extract_docx
from .hwp import extract_hwp
from .image import extract_image
from .pdf import extract_pdf

HANDLERS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".hwp": extract_hwp,
    ".jpg": extract_image,
    ".png": extract_image,
}


def ocr_node(state: dict) -> dict:
    if not state.get("input_files"):
        return {}
    texts = []
    is_visual = False
    for path in state["input_files"]:
        ext = Path(path).suffix.lower()
        result = HANDLERS[ext](path)
        if isinstance(result, tuple):
            texts.append(result[0])
            is_visual = is_visual or result[1]
        else:
            texts.append(result)
            if ext in (".jpg", ".png"):
                is_visual = True
    return {"ocr_text": "\n\n".join(texts), "needs_visual_review": is_visual}
