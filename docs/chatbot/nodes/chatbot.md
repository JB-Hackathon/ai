# Chatbot 노드

## 역할

`model_with_tools`로 messages 전체와 시스템 메시지를 보내 응답을 생성한다.  
LLM이 직접 tool call 여부를 결정한다.

- **tool call 없음** → AIMessage가 최종 응답 → END
- **tool call 있음** → AIMessage에 `tool_calls` 포함 → `tool_node`로 분기

## 시스템 메시지 구성

시스템 메시지에는 두 가지를 포함한다:

1. **페르소나**: 금융 광고 심의 전문가 챗봇
2. **심의 컨텍스트**: 현재 `review_result`, `law_list` 등 state 값

```python
system_content = f"""당신은 금융 광고 심의 전문가 챗봇입니다.
사용자가 1차 심의 결과를 검토하고 수정 요청하거나 질문할 수 있도록 도와주세요.

현재 심의 결과:
{state["review_result"]}

적용된 법령:
{chr(10).join(state["law_list"])}
"""
```

## 구현 패턴

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from .tools import law_review, expression_edit

_tools = [law_review, expression_edit]
_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
_model_with_tools = _llm.bind_tools(_tools)


def _build_system(state: ChatState) -> str:
    law_text = "\n".join(state["law_list"])
    return f"""당신은 금융 광고 심의 전문가 챗봇입니다.
사용자가 1차 심의 결과를 검토하고 수정 요청하거나 질문할 수 있도록 도와주세요.

현재 심의 결과:
{state["review_result"]}

적용된 법령:
{law_text}"""


async def chatbot_node(state: ChatState) -> dict:
    system = SystemMessage(content=_build_system(state))
    response = await _model_with_tools.ainvoke([system] + state["messages"])
    return {"messages": [response]}
```

## 입력 / 출력

| 항목 | 값 |
|------|-----|
| 입력 | `state["messages"]` 전체 + `state["review_result"]`, `state["law_list"]` (시스템 메시지 구성용) |
| 출력 | `{"messages": [AIMessage(...)]}` — `tool_calls` 유무로 분기 결정 |

## 구현 위치

`src/chatbot/nodes/chatbot.py`
