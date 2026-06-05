import base64

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


def extract_image(path: str) -> str:
    with open(path, "rb") as f:
        image_bytes = f.read()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = "image/jpeg" if ext == "jpg" else "image/png"
    b64 = base64.b64encode(image_bytes).decode()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    msg = HumanMessage(
        content=[
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": "이 이미지의 텍스트를 모두 추출해주세요."},
        ]
    )
    return llm.invoke([msg]).content
