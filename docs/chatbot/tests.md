# 테스트 케이스 명세

참고: 기존 테스트 패턴 — `tests/test_review.py` (LLM mock, captured prompts 검증)

---

## test_state.py

### `test_chat_state_fields`

`ChatState.__annotations__` 에 모든 필드가 존재하는지 확인.

```python
EXPECTED_FIELDS = {
    "review_result", "law_list", "checklist", "conditional_checklist",
    "content_text", "ocr_text", "channel_type", "content_category",
    "product_category", "business_sector", "eval_score", "eval_feedback",
    "review_passed", "needs_visual_review",
    "messages",
}

def test_chat_state_fields():
    assert EXPECTED_FIELDS == ChatState.__annotations__.keys()
```

---

## test_tools.py

공통 픽스처:

```python
SAMPLE_STATE = {
    "review_result": "기존 심의 결과",
    "law_list": ["자본시장법 제47조", "금융소비자보호법 제19조"],
    "checklist": ["허위 표현 없음"],
    "conditional_checklist": [],
    "content_text": "광고 텍스트",
    "ocr_text": "",
    "messages": [],
}
```

### `test_law_review_updates_review_result`

`law_review` tool 호출 시 `Command.update["review_result"]` 가 갱신되는지 확인.

- LLM을 mock하여 `"재작성된 심의 결과"` 반환
- 반환된 `Command.update["review_result"] == "재작성된 심의 결과"` 검증

### `test_law_review_prompt_includes_law_list`

`law_review` 가 LLM에 전달하는 메시지에 `law_list` 전체가 포함되는지 확인.

- captured prompts 방식으로 사용자 메시지 본문 캡처
- `"자본시장법 제47조"` 와 `"금융소비자보호법 제19조"` 가 메시지에 포함되어 있는지 검증

### `test_law_review_prompt_includes_user_instruction`

`user_instruction` 이 프롬프트에 포함되는지 확인.

- `user_instruction="○○ 법령 누락"` 으로 호출
- 캡처된 메시지 본문에 해당 문자열 포함 여부 검증

### `test_law_review_returns_tool_message`

`Command.update["messages"]` 에 `ToolMessage` 가 포함되는지, `tool_call_id` 가 일치하는지 확인.

### `test_expression_edit_updates_review_result`

`expression_edit` tool 호출 시 `Command.update["review_result"]` 가 갱신되는지 확인.

- LLM mock → `"수정된 심의 결과"` 반환
- `Command.update["review_result"] == "수정된 심의 결과"` 검증

### `test_expression_edit_prompt_includes_current_result`

`expression_edit` 가 LLM에 전달하는 메시지에 현재 `review_result` 가 포함되는지 확인.

- `review_result="기존 심의 결과"` 로 state 구성
- 캡처된 메시지에 해당 문자열 포함 여부 검증

### `test_expression_edit_prompt_excludes_law_list`

`expression_edit` 프롬프트에 `law_list` 가 포함되지 않아야 함 (전체 재심의 아님).

---

## test_chatbot_graph.py

### `test_chatbot_general_response`

tool call 없이 일반 응답으로 종료하는 경우.

- LLM mock: `tool_calls=[]` 인 AIMessage 반환
- 그래프 실행 후 `messages[-1]` 이 AIMessage 인지 확인
- `review_result` 변경 없음 확인

### `test_chatbot_law_review_tool_call`

LLM이 `law_review` tool call을 반환하는 경우 그래프가 tool_node → chatbot_node 순으로 실행되는지 확인.

- LLM mock 1차: `tool_calls=[{"name": "law_review", ...}]` 인 AIMessage 반환
- `law_review` tool mock: `review_result` 를 `"재작성된 심의 결과"` 로 갱신하는 Command 반환
- LLM mock 2차 (루프백): `tool_calls=[]` 인 AIMessage 반환
- 최종 `messages[-1]` 이 AIMessage 인지, `state["review_result"] == "재작성된 심의 결과"` 인지 확인

### `test_chatbot_expression_edit_tool_call`

`expression_edit` tool call 경로 동일 패턴으로 검증.

### `test_chatbot_graph_checkpointer_saves_state`

동일 `thread_id` 로 두 번 호출 시 이전 대화 이력이 이어지는지 확인.

- 1차 호출: `HumanMessage("질문1")` → 응답
- 2차 호출: `HumanMessage("질문2")` → 응답
- 2차 호출 결과의 `messages` 길이가 1차보다 긴지 (이력 누적) 확인
- 메모리 체크포인터(`MemorySaver`) 사용 (PostgreSQL 불필요)
