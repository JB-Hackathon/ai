from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel


class ChecklistOutput(BaseModel):
    items: list[str]


def checklist_node(state: dict) -> dict:
    law_text = "\n".join(state.get("law_list", []))
    prompt = f"""다음 내용을 심의할 때 사용할 체크리스트 항목을 작성해주세요.

## 심의 대상 텍스트
{state.get("input_text", "")}

## OCR 추출 텍스트
{state.get("ocr_text", "")}

## 관련 법령
{law_text}

심의 및 평가 기준으로 사용할 체크리스트 항목을 구체적으로 작성해주세요."""

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(ChecklistOutput)
    result = structured_llm.invoke(prompt)
    return {"checklist": result.items}
