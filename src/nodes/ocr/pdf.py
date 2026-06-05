import base64

import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def extract_pdf(path: str) -> tuple[str, bool]:
    doc = fitz.open(path)
    first_text = doc[0].get_text()
    if len(first_text.strip()) >= 50:
        text = "\n".join(page.get_text() for page in doc)
        return (text, False)
    # 스캔 PDF: 첫 페이지를 PNG로 렌더링 후 Gemini Vision으로 추출
    pix = doc[0].get_pixmap()
    png_bytes = pix.tobytes("png")
    text = _gemini_vision(png_bytes, "이 문서의 텍스트를 모두 추출해주세요.")
    return (text, True)


def _gemini_vision(image_bytes: bytes, prompt: str) -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    b64 = base64.b64encode(image_bytes).decode()
    msg = HumanMessage(
        content=[
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": prompt},
        ]
    )
    return llm.invoke([msg]).content
