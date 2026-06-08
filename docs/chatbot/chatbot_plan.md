# 챗봇 구축 계획

## Context

기존 Phase 1 시스템(`src/graph.py`)은 문서를 받아 **단방향 파이프라인**으로 심의 결과를 생성한다.  
`docs/chatbot/chatbot_workflow.png`는 심의 결과가 나온 **이후** 사용자와 대화하며 결과를 수정할 수 있는 **대화형 챗봇** 워크플로우를 정의한다.

워크플로우 요약:
- 사용자 쿼리 → `chatbot_node` (LLM이 tool call 여부 직접 결정)
- **Tool 호출 X** → AIMessage 반환 → END
- **Tool 호출 O** → `tool_node`
  - **Tool 1 (`law_review`)**: AI가 컨텍스트 법령을 일부 누락한 경우 → 법령 재검토 + 결과 반환
  - **Tool 2 (`expression_edit`)**: 1차 심의 결과 표현 수정 요구 → 표현 수정 + 결과 반환
- 수정 결과 → 루프백 (`chatbot_node`로)

---

## 필요 컴포넌트

### 1. State — `src/chatbot/state.py`

새로운 `ChatState` TypedDict (기존 `ReviewState`와 별개)

**Phase 1 체크포인터에서 주입 (읽기 전용 컨텍스트)**

| 필드 | 타입 | 출처 |
|------|------|------|
| `review_result` | `str` | Phase 1 `review_node` 결과 |
| `law_list` | `list[str]` | Phase 1 `rag_node` 결과 |
| `checklist` | `list[str]` | Phase 1 `checklist_node` 결과 |
| `conditional_checklist` | `list[str]` | Phase 1 `checklist_node` 결과 |
| `content_text` | `str` | 원본 광고 텍스트 |
| `ocr_text` | `str` | OCR 추출 텍스트 |
| `channel_type` | `str` | 채널 유형 |
| `content_category` | `str` | 콘텐츠 유형 |
| `product_category` | `str \| None` | 상품군 |
| `business_sector` | `str` | 업권 |
| `eval_score` | `float` | 1차 평가 점수 |
| `eval_feedback` | `str` | 1차 평가 피드백 |
| `review_passed` | `bool` | 심의 통과 여부 |
| `needs_visual_review` | `bool` | 이미지/스캔 PDF 포함 여부 |

**챗봇 고유 필드**

| 필드 | 타입 | 역할 |
|------|------|------|
| `messages` | `Annotated[list, add_messages]` | 대화 이력 (HumanMessage / AIMessage / ToolMessage) |

---

### 2. 노드 & 도구 — `src/chatbot/nodes/`

#### `chatbot.py` — `chatbot_node`
- `model_with_tools`로 messages 전체 + 시스템 메시지(페르소나 + 심의 컨텍스트) 전달
- LLM이 tool call 여부를 직접 결정
- tool call 없음 → AIMessage 반환 → END
- tool call 있음 → AIMessage에 `tool_calls` 포함 → `tool_node`로 분기

#### `tools.py` — tool 정의
- `law_review`: 기존 `law_list` 전체를 반영해 심의 결과 재작성. `InjectedState`로 state 접근, `Command`로 `review_result` 갱신
- `expression_edit`: 사용자가 요청한 특정 표현만 수정. 동일 패턴

---

### 3. 그래프 — `src/chatbot/graph.py`

```
START → chatbot_node
           ├─(tool call 없음)─→ END
           └─(tool call 있음)─→ tool_node → chatbot_node
```

- 조건 엣지: `state["messages"][-1].tool_calls` 유무로 분기
- `tool_node`: LangGraph 내장 `ToolNode([law_review, expression_edit])`
- 체크포인터: 기존 `AsyncPostgresSaver` 재사용 (같은 DB 인스턴스 공유)
  - Phase 1 thread_id = `str(content_version_id)` (숫자 문자열, 예: `"42"`)
  - 챗봇 thread_id = `chat_threads.thread_id` (UUID) → 형식이 달라 충돌 없음

---

### 4. API 엔드포인트 — `main.py` 추가

```
POST /thread/{thread_id}   (thread_id: UUID)
Body: { "message": str }
Response: { "reply": str }
```

**초기 상태 조회 흐름:**
1. `chat_threads` 조회 → `content_version_id` 획득
2. Phase 1 체크포인터에서 `str(content_version_id)` thread 상태 조회 → `ChatState` 초기값 14개 필드 추출
3. 챗봇 그래프에 초기값 + `HumanMessage` 주입 후 `ainvoke` → `messages[-1].content` 반환

---

### 5. 테스트 — `tests/chatbot/`

| 파일 | 내용 |
|------|------|
| `test_state.py` | ChatState 필드 정의 확인 |
| `test_tools.py` | `law_review`, `expression_edit` tool 실행 후 `review_result` 갱신 확인 |
| `test_chatbot_graph.py` | 전체 그래프 통합 테스트 (일반 응답 / tool 호출 / 루프) |

---

## 재사용할 기존 코드

| 재사용 대상 | 경로 | 활용처 |
|------------|------|--------|
| `review_node` 프롬프트 | `src/nodes/review.py` | tool 1·2 결과 재생성 |
| `AsyncPostgresSaver` 설정 | `main.py` (lifespan) | 챗봇 체크포인터 |
| Gemini 클라이언트 패턴 | 모든 노드 | LLM 호출 |
