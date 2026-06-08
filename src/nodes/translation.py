from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

_SYSTEM = """\
너는 금융 콘텐츠 전문 번역가다.
원문에 충실한 직역을 원칙으로 하며, 금융 용어·수치·상품명의 정확성을 최우선으로 한다.\
"""

_USER_TEMPLATE = """\
다음 텍스트를 한국어로 번역하라.

규칙:
- 원문에 충실한 직역 (의역 최소화)
- 수치·금리·상품명은 원문을 괄호 안에 병기 (예: 3% 이자율(3% interest rate))
- 번역만 수행하며 심의 의견·평가·수정 제안을 추가하지 말 것
- 번역 결과만 출력하고 설명·주석·서두·마무리 문장 없이 번역문만 출력

원문 언어: {language}
원문:
{text}
"""


def translation_node(state: dict) -> dict:
    if state.get("language_code") == "ko":
        return {}

    updates = {
        "original_content_text": state.get("content_text", ""),
        "original_ocr_text": state.get("ocr_text", ""),
    }
    if state.get("content_text"):
        updates["content_text"] = _translate(state["content_text"], state["language_code"])
    if state.get("ocr_text"):
        updates["ocr_text"] = _translate(state["ocr_text"], state["language_code"])

    return updates


def _translate(text: str, language_code: str) -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=_USER_TEMPLATE.format(language=language_code, text=text)),
    ]
    return llm.invoke(messages).content
