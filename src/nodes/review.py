import base64
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

_SYSTEM = "당신은 금융 광고 심의 전문가입니다. 체크리스트와 법령을 기반으로 심의 결과서를 작성해주세요."


def review_node(state: dict) -> dict:
    checklist_text = "\n".join(f"- {item}" for item in state.get("checklist", []))
    law_text = "\n".join(state.get("law_list", []))
    feedback = state.get("eval_feedback", "")

    conditional_text = "\n".join(f"- {item}" for item in state.get("conditional_checklist", []))

    body = f"""## 심의 대상 텍스트
{state.get("content_text", "")}

## OCR 추출 텍스트
{state.get("ocr_text", "")}

## 체크리스트
{checklist_text}

## 관련 법령
{law_text}
"""
    if conditional_text:
        body += f"\n## 조건부 참고항목 (직접 적용 기준은 아니나 맥락 참고용)\n{conditional_text}"
    if feedback:
        body += f"\n## 이전 평가 피드백 (개선 필요)\n{feedback}"
    body += "\n\n위 내용을 바탕으로 심의 결과서를 작성해주세요."

    user_content: list = []
    if state.get("needs_visual_review") and state.get("content_file_path"):
        for path in state["content_file_path"]:
            if Path(path).suffix.lower() in (".jpg", ".png"):
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = Path(path).suffix.lower()
                mime = "image/jpeg" if ext == ".jpg" else "image/png"
                user_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    user_content.append({"type": "text", "text": body})

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    result = llm.invoke([SystemMessage(content=_SYSTEM), HumanMessage(content=user_content)])
    return {"review_result": result.content}
