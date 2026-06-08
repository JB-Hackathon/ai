# 챗봇 워크플로우 개요

## 목적

1차 심의 완료 후, 사용자가 심의 결과를 검토하고 수정 요청 또는 질문을 할 수 있는 대화형 챗봇 시스템.  
`src/graph.py`의 단방향 파이프라인이 생성한 결과를 기반으로, 사용자와의 대화를 통해 심의 결과를 점진적으로 개선한다.

## 기술 스택

| 역할 | 기술 |
|------|------|
| LLM | gemini-2.5-flash (Google) — tool call 여부 판단 + 응답 생성 |
| 그래프 프레임워크 | LangGraph StateGraph + 내장 ToolNode |
| 체크포인터 | AsyncPostgresSaver (Phase 1과 동일 DB 인스턴스) |
| 서비스 | FastAPI REST API (`main.py` 에 엔드포인트 추가) |

## 코드 디렉터리 구조

```
ai/
├── src/
│   ├── main.py                   # FastAPI 앱 — POST /thread/{thread_id} 추가
│   └── chatbot/
│       ├── __init__.py
│       ├── state.py              # ChatState TypedDict
│       ├── graph.py              # LangGraph StateGraph (챗봇)
│       └── nodes/
│           ├── __init__.py
│           ├── chatbot.py        # chatbot_node (model_with_tools)
│           └── tools.py          # @tool 정의 (law_review, expression_edit)
└── tests/
    └── chatbot/
        ├── __init__.py
        ├── test_state.py
        ├── test_tools.py
        └── test_chatbot_graph.py
```

## 워크플로우 요약

```
사용자 쿼리
    ↓
chatbot_node (model_with_tools)
    ├─ tool call 없음 ─→ AIMessage → END
    └─ tool call 있음 ─→ tool_node
                              ├─ law_review: 법령 재검토 + 심의 결과 재작성
                              └─ expression_edit: 특정 표현 수정
                          ↓
                      chatbot_node (루프)
```

- `chatbot_node`의 LLM이 사용자 요청을 보고 tool 호출 여부를 직접 결정한다.
- tool 호출이 없으면 AIMessage로 바로 응답하고 종료한다.
- tool 실행 후 ToolMessage가 messages에 추가되고 `chatbot_node`로 루프백한다.

## 검증 방법

1. **단위**: 각 tool 함수를 독립 호출하여 출력 확인
2. **통합 (일반 응답)**: `POST /thread/{thread_id}`에 일반 질문 전송 → tool 호출 없이 AIMessage 반환 확인
3. **통합 (law_review)**: 법령 누락 지적 메시지 전송 → `law_review` tool 실행 + `review_result` 갱신 확인
4. **통합 (expression_edit)**: 표현 수정 요청 전송 → `expression_edit` tool 실행 + `review_result` 갱신 확인
5. **루프**: tool 실행 후 `chatbot_node`로 루프백하여 추가 응답 생성 확인

## 워크플로우 다이어그램

![챗봇 워크플로우](./chatbot_workflow.png)
