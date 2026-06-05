# 1차 심의 AI 모듈 구현 계획 (PostgreSQL 제외)

## 개요

PostgreSQL/pgvector는 추후 연동하고, 핵심 로직(OCR, LLM 심의, 평가, FastAPI)을 먼저 구현한다. RAG 노드는 빈 stub으로 처리한다.

---

## 구현 단위 및 순서

### Unit 1 — State 정의
**파일**: `src/state.py`

- `ReviewState` TypedDict 정의 ([state.md](./state.md) 기준)
- `Annotated[list, add_messages]` import 포함
- 모든 노드가 의존하는 기반 파일

**참고**: [input_contents.md](../input_contents.md)

---

### Unit 2 — OCR 노드
**파일**: `src/nodes/ocr/__init__.py`, `pdf.py`, `docx.py`, `hwp.py`, `image.py`

| 파일 | 함수 | 처리 방식 |
|------|------|-----------|
| `pdf.py` | `extract_pdf(path) -> tuple[str, bool]` | PyMuPDF, 50자 미만 시 Gemini Vision fallback |
| `docx.py` | `extract_docx(path) -> str` | python-docx paragraphs 순회 |
| `hwp.py` | `extract_hwp(path) -> str` | libhwp 파싱 |
| `image.py` | `extract_image(path) -> str` | Gemini Vision API |
| `__init__.py` | `ocr_node(state)` | 확장자별 핸들러 디스패치 |

출력: `{"ocr_text": str, "needs_visual_review": bool}`

**참고**: [nodes/ocr.md](./nodes/ocr.md)

---

### Unit 3 — RAG stub
**파일**: `src/nodes/rag.py`

- `rag_node(state) -> dict`
- `{"law_list": [], "needs_visual_review": state.get("needs_visual_review", False)}` 반환
- 함수 시그니처는 실제 구현과 동일하게 유지

**참고**: [nodes/rag.md](./nodes/rag.md)

---

### Unit 4 — 체크리스트 노드
**파일**: `src/nodes/checklist.py`

- `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` + `with_structured_output(ChecklistOutput)`
- `ChecklistOutput(BaseModel)`: `items: list[str]`
- 입력: `input_text`, `ocr_text`, `law_list`
- 출력: `{"checklist": result.items}`

**참고**: [nodes/checklist.md](./nodes/checklist.md)

---

### Unit 5 — 심의 노드
**파일**: `src/nodes/review.py`

- `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`
- `needs_visual_review == True` 시 이미지 파일을 VLM 요청에 포함
- 재심의 시 `eval_feedback`을 프롬프트에 포함
- 출력: `{"review_result": str}`

**참고**: [nodes/review.md](./nodes/review.md)

---

### Unit 6 — 평가자 노드
**파일**: `src/nodes/evaluator.py`

- `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` + `with_structured_output(EvalOutput)`
- `EvalOutput(BaseModel)`: `score: float`, `feedback: str`
- `loop_count + 1` 증가
- `review_passed`: `score >= 80` → True
- 출력: `{"eval_score", "eval_feedback", "loop_count", "review_passed"}`

**참고**: [nodes/evaluator.md](./nodes/evaluator.md)

---

### Unit 7 — Graph 조립
**파일**: `src/graph.py`

```
START -> ocr_node -> rag_node -> checklist_node -> review_node -> evaluator_node
evaluator_node:
  score >= 80 or loop_count >= 3 → END
  else → review_node
```

- checkpointer: `MemorySaver` (PostgreSQL 연동 전 임시)
- 조건부 엣지: `should_continue(state)` 라우터 함수

**참고**: [graph.md](./graph.md), [memory.md](./memory.md), [overview.md](./overview.md)

---

### Unit 8 — FastAPI 엔트리포인트
**파일**: `src/main.py`

구현 엔드포인트:
- `POST /review` — multipart/form-data, 파일 임시 저장 후 graph 실행

제외 (PostgreSQL 연동 후):
- `GET /review/{thread_id}`
- `PATCH /review/{thread_id}`
- `POST /ingest`

**참고**: [api.md](./api.md), [setup.md](./setup.md)

---

## 코드 품질

**ruff** (`pyproject.toml` 설정):
- 각 Unit 완성 후 `ruff check src/` + `ruff format src/` 실행
- line-length = 100, target-version = "py311"

---

## 테스트 전략 (pytest + mock)

위치: `tests/`
LLM 호출 노드는 `unittest.mock.patch`로 Gemini 응답 mock.

| Unit | 테스트 파일 | 주요 케이스 |
|------|------------|------------|
| 1 | `tests/test_state.py` | TypedDict 필드 존재 확인 |
| 2 | `tests/test_ocr.py` | 디지털 PDF, 스캔 PDF(mock), DOCX, 이미지(mock), HWP |
| 3 | `tests/test_rag.py` | 빈 law_list 반환, needs_visual_review 전달 |
| 4 | `tests/test_checklist.py` | mock LLM → checklist 리스트 반환 확인 |
| 5 | `tests/test_review.py` | 텍스트 전용, 이미지 포함(needs_visual_review=True) |
| 6 | `tests/test_evaluator.py` | score>=80 → passed, loop_count 증가, 강제종료 |
| 7 | `tests/test_graph.py` | graph.invoke 전체 흐름 (모든 LLM mock) |
| 8 | `tests/test_main.py` | FastAPI TestClient, POST /review 응답 스키마 확인 |

전체 실행: `ruff check src/ tests/` → `pytest tests/`

---

## 제외 항목 (PostgreSQL 연동 후 구현)

- `src/vector_store/store.py`
- `src/nodes/rag.py` 실제 구현
- `GET /review/{thread_id}`, `PATCH /review/{thread_id}`, `POST /ingest`
- `AsyncPostgresSaver` → `MemorySaver` 교체
