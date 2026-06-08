# Law Review Tool

## 역할

사용자가 법령 누락을 지적한 경우, 기존 `law_list` 전체를 빠짐없이 반영하여 심의 결과서(`review_result`)를 재작성한다.  
`chatbot_node`의 LLM이 이 tool을 호출하기로 결정하면 `tool_node`를 통해 실행된다.

## 핵심 전제

- **RAG 재검색 없음** — `law_list`는 Phase 1 `rag_node`가 이미 선별한 전체 목록이다. AI가 1차 심의 시 일부를 누락했을 뿐, 목록 자체는 완전하다.
- `law_list` 전체를 프롬프트에 포함시켜 재작성하면 누락 없이 반영된다.

## 처리 흐름

1. `InjectedState`로 `law_list`, `checklist`, `content_text`, `ocr_text`, `conditional_checklist` 접근
2. 전체 컨텍스트 + `user_instruction`으로 Gemini 호출 → 심의 결과서 재작성
3. `Command`를 반환하여 `review_result` 갱신 + ToolMessage를 messages에 추가

## 구현 패턴

```python
from typing import Annotated
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import InjectedState, InjectedToolCallId
from langgraph.types import Command

_SYSTEM = "당신은 금융 광고 심의 전문가입니다. 체크리스트와 법령을 기반으로 심의 결과서를 작성해주세요."

@tool
async def law_review(
    user_instruction: str,
    state: Annotated[ChatState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """법령이 누락된 경우, 기존 law_list 전체를 반영해 심의 결과를 재작성합니다."""
    checklist_text = "\n".join(f"- {item}" for item in state["checklist"])
    law_text = "\n".join(state["law_list"])
    conditional_text = "\n".join(f"- {item}" for item in state["conditional_checklist"])

    body = f"""## 심의 대상 텍스트
{state["content_text"]}

## OCR 추출 텍스트
{state["ocr_text"]}

## 체크리스트
{checklist_text}

## 관련 법령 (전체 목록)
{law_text}
"""
    if conditional_text:
        body += f"\n## 조건부 참고항목 (직접 적용 기준은 아니나 맥락 참고용)\n{conditional_text}"

    body += f"\n## 사용자 지적 사항\n{user_instruction}"
    body += "\n\n위 내용을 바탕으로 법령을 빠짐없이 반영하여 심의 결과서를 재작성해주세요."

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    response = await llm.ainvoke([SystemMessage(content=_SYSTEM), HumanMessage(content=body)])
    new_result = response.content

    return Command(update={
        "review_result": new_result,
        "messages": [ToolMessage(content=new_result, tool_call_id=tool_call_id)],
    })
```

## 프롬프트 구성

- 모델: `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`
- 시스템 프롬프트: `"당신은 금융 광고 심의 전문가입니다. 체크리스트와 법령을 기반으로 심의 결과서를 작성해주세요."`
- 사용자 메시지 구성 (f-string):
  1. `## 심의 대상 텍스트` — `content_text`
  2. `## OCR 추출 텍스트` — `ocr_text`
  3. `## 체크리스트` — `"- {item}"` 형식
  4. `## 관련 법령 (전체 목록)` — `law_list` 줄바꿈 구분
  5. `## 조건부 참고항목` — `conditional_checklist` 존재 시만 포함
  6. `## 사용자 지적 사항` — `user_instruction`
  7. 마무리 지시문: `"위 내용을 바탕으로 법령을 빠짐없이 반영하여 심의 결과서를 재작성해주세요."`

## 재사용

- 심의 결과 작성 프롬프트 패턴: `src/nodes/review.py` 참고

## 구현 위치

`src/chatbot/nodes/tools.py` — `law_review` 함수
