# 챗봇 구현 순서

참고: `chatbot_plan.md`, `chatbot_workflow.png`  
규칙: 각 Unit 완성 후 `ruff check` → `pytest` 순서로 반드시 실행한다.

---

## Unit 1 — ChatState 정의

**목적:** 모든 노드가 공유할 상태 스키마 확정

생성 파일:
- `src/chatbot/__init__.py`
- `src/chatbot/state.py`
- `tests/chatbot/__init__.py`
- `tests/chatbot/test_state.py`

검증:
```bash
ruff check src/chatbot/ tests/chatbot/test_state.py
pytest tests/chatbot/test_state.py
```

---

## Unit 2 — Tool 정의

**목적:** `law_review`, `expression_edit` tool 구현

생성 파일:
- `src/chatbot/nodes/__init__.py`
- `src/chatbot/nodes/tools.py`
- `tests/chatbot/test_tools.py`

의존: Unit 1 (`ChatState`)  
참고: `src/nodes/review.py` — 심의 결과 작성 프롬프트 패턴  
주의:
- `law_review`: RAG 재검색 없음, `law_list`는 그대로 사용
- `InjectedState`로 state 접근, `Command`로 `review_result` + ToolMessage 동시 갱신

검증:
```bash
ruff check src/chatbot/ tests/chatbot/test_tools.py
pytest tests/chatbot/test_tools.py
```

---

## Unit 3 — Chatbot 노드

**목적:** `model_with_tools` 바인딩 + `chatbot_node` 구현

생성 파일:
- `src/chatbot/nodes/chatbot.py`

의존: Unit 2 (tools)  
참고: `src/nodes/review.py` — Gemini 클라이언트 패턴

검증:
```bash
ruff check src/chatbot/nodes/chatbot.py
```

---

## Unit 4 — 챗봇 그래프

**목적:** `chatbot_node` + `ToolNode`를 연결하는 StateGraph 조립

```
START → chatbot_node
           ├─(tool call 없음)─→ END
           └─(tool call 있음)─→ tool_node → chatbot_node
```

생성 파일:
- `src/chatbot/graph.py`
- `tests/chatbot/test_chatbot_graph.py`

의존: Unit 2–3 (tools + chatbot_node)  
참고: `src/graph.py` — AsyncPostgresSaver 설정 패턴  
주의: 챗봇 thread_id = UUID (`chat_threads.thread_id`), Phase 1 thread_id = `str(content_version_id)` — 충돌 없음

검증:
```bash
ruff check src/chatbot/ tests/chatbot/
pytest tests/chatbot/
```

---

## Unit 5 — API 엔드포인트

**목적:** `POST /thread/{thread_id}` 엔드포인트 추가

수정 파일:
- `main.py`

초기 상태 조회 흐름:
1. `chat_threads` 조회 → `content_version_id` 획득
2. Phase 1 체크포인터에서 `str(content_version_id)` thread 상태 조회 → `ChatState` 초기값 추출
3. 챗봇 그래프에 초기값 + `HumanMessage` 주입 후 `ainvoke` → `messages[-1].content` 반환

의존: Unit 4 (챗봇 그래프)

검증:
```bash
ruff check src/ tests/
pytest tests/
```

E2E 수동 테스트 시나리오:
1. `POST /review/{content_version_id}` → Phase 1 심의 완료
2. `POST /thread/{thread_id}` (일반 질문) → tool 호출 없이 AIMessage 반환
3. `POST /thread/{thread_id}` ("○○ 법령 누락") → `law_review` tool 실행, 수정된 심의 결과 반환
4. `POST /thread/{thread_id}` ("표현 수정 요청") → `expression_edit` tool 실행, 수정된 심의 결과 반환
