from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel


class EvalOutput(BaseModel):
    score: float
    feedback: str


def evaluator_node(state: dict) -> dict:
    checklist_text = "\n".join(f"- {item}" for item in state.get("checklist", []))
    law_text = "\n".join(state.get("law_list", []))
    prompt = f"""다음 심의 결과서를 체크리스트 기준으로 평가해주세요.

## 체크리스트
{checklist_text}

## 관련 법령
{law_text}

## 심의 대상 텍스트
{state.get("input_text", "")}

## OCR 추출 텍스트
{state.get("ocr_text", "")}

## 심의 결과서
{state.get("review_result", "")}

0~100점 사이 점수와 구체적인 피드백을 작성해주세요."""

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    structured_llm = llm.with_structured_output(EvalOutput)
    result = structured_llm.invoke(prompt)

    loop_count = state.get("loop_count", 0) + 1
    return {
        "eval_score": result.score,
        "eval_feedback": result.feedback,
        "loop_count": loop_count,
        "review_passed": result.score >= 80,
    }
