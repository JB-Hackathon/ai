# 메모리 아키텍처

## 개요

1차 심의 워크플로우는 두 가지 메모리 레이어를 사용한다.

| 구분 | 구현 | 역할 |
|------|------|------|
| 단기 메모리 | `AsyncPostgresSaver` (checkpointer) | 그래프 실행 중 각 step의 state 스냅샷 저장 |
| 장기 메모리 | 동일 checkpointer DB + `thread_id` | 심의 완료 후 챗봇이 결과에 접근/수정 |

---

## 단기 메모리 — Checkpointer

### 역할

- 각 노드 실행 후 `ReviewState` 스냅샷을 PostgreSQL에 저장
- `messages: Annotated[list, add_messages]` 필드가 재심의 루프 전반에 걸쳐 올바르게 누적되도록 보장
- 그래프가 비정상 종료되어도 마지막 checkpoint에서 재개 가능

### 구현

패키지: `langgraph-checkpoint-postgres` (psycopg3 필요 — `psycopg[binary]>=3.0`)

checkpointer는 FastAPI `lifespan` 이벤트에서 초기화하여 앱 수명 동안 유지한다. 요청마다 새로 열면 연결 풀이 낭비되고 graph가 매번 재컴파일된다.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()  # 최초 1회 — langgraph_checkpoint 테이블 생성
        app.state.graph = workflow.compile(checkpointer=checkpointer)
        yield  # 앱 수명 동안 연결 유지

app = FastAPI(lifespan=lifespan)
```

엔드포인트에서는 `request.app.state.graph`로 그래프 인스턴스를 참조한다.

### 호출 방법

`/review` 요청 시 UUID `thread_id`를 생성하여 LangGraph config에 전달한다.

```python
import uuid
from langgraph.graph import StateGraph

thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

result = await graph.ainvoke(initial_state, config=config)
```

`thread_id`는 `ReviewState`에 포함하지 않는다. LangGraph config 영역에서 관리한다.

---

## 장기 메모리 — thread_id 기반 상태 접근

### 역할

1차 심의 완료 후, 준법 자문가가 챗봇을 통해 심의 결과(`review_result`, `checklist` 등)를 수정하거나 검토한다. 챗봇은 `thread_id`를 이용해 동일한 checkpointer DB에서 최종 state를 로드하고 수정 사항을 반영한다.

### 흐름

```
POST /review
  → thread_id 생성 (UUID)
  → graph.ainvoke(state, config) 실행
  → 심의 완료 → response에 thread_id 포함

챗봇 (준법 자문가)
  → thread_id로 최종 state 로드
  → review_result / checklist 수정
  → 수정 사항 저장
```

### 상태 로드 (get_state)

```python
config = {"configurable": {"thread_id": thread_id}}
snapshot = await graph.aget_state(config)
state = snapshot.values  # 최종 ReviewState
```

### 상태 수정 (update_state)

```python
config = {"configurable": {"thread_id": thread_id}}
await graph.aupdate_state(config, {
    "review_result": "수정된 심의 결과...",
    "checklist": ["수정된 체크리스트 항목..."],
})
```

---

## 인프라

- **PostgreSQL 인스턴스**: 벡터 스토어(pgvector)와 동일한 인스턴스 공유 가능
- **자동 생성 테이블**: `checkpointer.setup()` 호출 시 `langgraph_checkpoint` 테이블 자동 생성
- **환경 변수**: `DATABASE_URL` — 기존 벡터 스토어와 동일한 변수 사용
