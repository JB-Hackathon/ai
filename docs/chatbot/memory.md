# 메모리 아키텍처

## 개요

챗봇은 두 가지 체크포인터 영역을 활용한다.

| 구분 | thread_id 형식 | 역할 |
|------|---------------|------|
| Phase 1 체크포인터 (읽기) | `str(content_version_id)` (숫자 문자열, 예: `"42"`) | 1차 심의 결과(`review_result`, `law_list` 등) 로드 |
| 챗봇 체크포인터 (읽기/쓰기) | `chat_threads.thread_id` (UUID, 예: `"550e8400-..."`) | 챗봇 대화 이력 및 수정된 상태 저장 |

두 체크포인터 모두 동일한 `AsyncPostgresSaver` 인스턴스(같은 DB)를 공유하며, thread_id 형식이 달라 충돌하지 않는다.

---

## Phase 1 상태 로드

챗봇 첫 메시지 처리 시 Phase 1 체크포인터에서 심의 결과를 읽어 `ChatState` 초기값을 구성한다.

```python
config = {"configurable": {"thread_id": str(content_version_id)}}
snapshot = await phase1_graph.aget_state(config)
phase1_values = snapshot.values  # ReviewState 최종값
```

추출하는 필드:

| Phase 1 필드 | ChatState 필드 |
|-------------|---------------|
| `review_result` | `review_result` |
| `law_list` | `law_list` |
| `checklist` | `checklist` |
| `conditional_checklist` | `conditional_checklist` |
| `content_text` | `content_text` |
| `ocr_text` | `ocr_text` |
| `channel_type` | `channel_type` |
| `content_category` | `content_category` |
| `product_category` | `product_category` |
| `business_sector` | `business_sector` |
| `eval_score` | `eval_score` |
| `eval_feedback` | `eval_feedback` |
| `review_passed` | `review_passed` |
| `needs_visual_review` | `needs_visual_review` |

---

## 챗봇 대화 이력 저장

챗봇 그래프는 UUID thread_id로 실행되며, 매 노드 완료 시 `ChatState` 스냅샷이 PostgreSQL에 저장된다.

```python
config = {"configurable": {"thread_id": str(chat_thread_id)}}
result = await chatbot_graph.ainvoke(initial_state, config=config)
```

동일 thread_id로 재호출하면 이전 대화 이력(`messages`)이 체크포인터에서 자동 복원된다.  
`add_messages` 리듀서가 새 메시지를 기존 목록에 누적한다.

---

## lifespan 설정

Phase 1 그래프와 챗봇 그래프는 동일한 `checkpointer`를 공유한다. 연결 풀 낭비를 방지하기 위해 `lifespan`에서 한 번만 초기화한다.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        app.state.phase1_graph = phase1_workflow.compile(checkpointer=checkpointer)
        app.state.chatbot_graph = chatbot_workflow.compile(checkpointer=checkpointer)
        yield
```

---

## 인프라

- **PostgreSQL 인스턴스**: Phase 1 벡터 스토어(pgvector)와 동일한 인스턴스 공유 가능
- **자동 생성 테이블**: `checkpointer.setup()` 호출 시 `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` 4개 테이블 자동 생성
- **환경 변수**: `DATABASE_URL` — Phase 1과 동일한 변수 사용
