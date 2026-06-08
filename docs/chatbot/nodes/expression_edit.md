# Expression Edit Tool

## 역할

사용자가 요청한 특정 표현·문구만 수정하여 `review_result`를 갱신한다.  
전체 심의를 재실행하지 않으며, 지정된 부분만 교체한다.  
`chatbot_node`의 LLM이 이 tool을 호출하기로 결정하면 `tool_node`를 통해 실행된다.

## 핵심 전제

- **전체 재심의 아님** — 법령·체크리스트 기반 재평가가 아니라, 특정 표현의 문구 수정이다.
- 수정 범위는 `user_instruction`이 지정한 부분으로 한정한다.

## 처리 흐름

1. `InjectedState`로 `review_result` 접근
2. 현재 `review_result` + `user_instruction`으로 Gemini 호출 → 요청된 표현만 수정
3. `Command`를 반환하여 `review_result` 갱신 + ToolMessage를 messages에 추가

## 구현 패턴

```python
from typing import Annotated
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import InjectedState, InjectedToolCallId
from langgraph.types import Command

_SYSTEM = "당신은 금융 광고 심의 전문가입니다. 사용자가 요청한 특정 표현만 수정하여 심의 결과서를 반환해주세요. 수정 범위 외의 내용은 그대로 유지하세요."

@tool
async def expression_edit(
    user_instruction: str,
    state: Annotated[ChatState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """1차 심의 결과에서 특정 표현·문구만 수정합니다."""
    body = f"""## 현재 심의 결과서
{state["review_result"]}

## 수정 요청
{user_instruction}

요청된 표현·문구만 수정하여 심의 결과서를 반환해주세요. 수정 범위 외의 내용은 그대로 유지하세요."""

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
- 시스템 프롬프트: `"당신은 금융 광고 심의 전문가입니다. 사용자가 요청한 특정 표현만 수정하여 심의 결과서를 반환해주세요. 수정 범위 외의 내용은 그대로 유지하세요."`
- 사용자 메시지 구성 (f-string):
  1. `## 현재 심의 결과서` — `review_result` 전문
  2. `## 수정 요청` — `user_instruction`
  3. 마무리 지시문: `"요청된 표현·문구만 수정하여 심의 결과서를 반환해주세요. 수정 범위 외의 내용은 그대로 유지하세요."`

## 재사용

- 프롬프트 패턴: `src/nodes/review.py` 참고

## 구현 위치

`src/chatbot/nodes/tools.py` — `expression_edit` 함수
