# 준법 자문가 Agent - 1차 심의 워크플로우 구현 계획

## Context

금융 광고/콘텐츠에 대한 준법 자문 AI 시스템을 구축한다.
사용자가 제출한 텍스트 또는 파일(이미지/PDF/DOCX/HWP)을 분석하고,
관련 법령을 RAG로 선별하여 LLM/VLM 기반 심의를 수행한다.
심의 결과는 내부 평가자가 검증하며, 기준 미달 시 최대 3회 재심의한다.
FastAPI 서버로 노출하여 backend와 연동한다.

**확정 스택**:
- LLM/VLM: gemini-2.5-flash (Google) — 텍스트 + 이미지 통합 처리
- OCR: PyMuPDF(PDF 텍스트/스캔 감지), Gemini Vision(이미지/스캔PDF), python-docx(DOCX), libhwp(HWP)
- 벡터 스토어: PostgreSQL + pgvector + Gemini text-embedding-004
- RAG 데이터: `data/` 서브모듈에서 제공 예정 (인덱싱 파이프라인 포함)
- 서비스: FastAPI REST API

---

## 디렉터리 구조

```
ai/
├── src/
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   ├── state.py             # LangGraph State (TypedDict)
│   ├── graph.py             # LangGraph StateGraph 조립
│   ├── nodes/
│   │   ├── ocr.py           # OCR 노드 (파일 -> 텍스트)
│   │   ├── rag.py           # RAG 노드 (법령 선별)
│   │   ├── checklist.py     # 체크리스트 생성 노드
│   │   ├── review.py        # 심의 노드 (LLM / VLM 분기)
│   │   └── evaluator.py     # 평가자 노드
│   └── vector_store/
│       └── store.py         # ChromaDB 초기화 및 인덱싱
├── requirements.txt
└── .env.example
```

---

## State 정의 (`src/state.py`)

```python
class ReviewState(TypedDict):
    # 사용자 입력 (요청 시 채워짐)
    input_text: str
    input_files: list[dict]        # [{filename, content_bytes, mime_type}]
    channel: str
    content_type: str
    product_category: str | None
    industry: str
    language: str

    # Agent 실행 중 채워지는 필드
    ocr_text: str                  # OCR 추출 텍스트
    law_list: list[str]            # RAG로 찾은 법령 조항
    checklist: list[str]           # LLM이 생성한 심의 체크리스트
    review_result: str             # 심의 결과서 (초안)
    eval_score: float              # 평가 점수 (0~100)
    eval_feedback: str             # 평가 피드백
    loop_count: int                # 재심의 횟수 (무한 루프 방지)
    messages: list                 # 대화 로그
```

---

## LangGraph 노드 & 엣지 (`src/graph.py`)

### 노드 목록

| 노드 | 역할 |
|------|------|
| `ocr_node` | 파일 -> 텍스트 추출 (PyMuPDF / Gemini Vision / docx / libhwp) |
| `rag_node` | input_text + ocr_text를 쿼리로 PostgreSQL+pgvector에서 법령 검색 |
| `checklist_node` | gemini-2.5-flash로 체크리스트 생성 |
| `review_node` | gemini-2.5-flash로 심의 결과 작성 (텍스트 + 이미지 통합 처리) |
| `evaluator_node` | 체크리스트 대비 심의 결과 평가, 점수/피드백 반환 |

### 라우팅 (Conditional Edges)

```
START -> (input_files 있음) -> ocr_node -> rag_node
      -> (input_files 없음) -> rag_node

rag_node -> checklist_node -> review_node

review_node -> evaluator_node
  -> (score >= 80 or loop_count >= 3) -> END
  -> (score < 80 and loop_count < 3)  -> review_node (루프)
```

---

## 핵심 구현 사항

### OCR (`src/nodes/ocr.py`)
- PDF (디지털): `PyMuPDF (fitz)` — 첫 페이지 50자 이상 시 `page.get_text()` 고속 추출
- PDF (스캔): 텍스트 부족 시 `gemini-2.5-flash` Vision API fallback
- DOCX: `python-docx` — `Document.paragraphs`
- 이미지 (jpg/png): `gemini-2.5-flash` Vision API
- HWP: `libhwp`

### RAG (`src/vector_store/store.py`, `src/nodes/rag.py`)
- `data/` 디렉터리의 법령 텍스트를 `RecursiveCharacterTextSplitter`로 청킹
- `GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")`로 임베딩 (768차원)
- PostgreSQL + pgvector 저장 (`DATABASE_URL`)
- 쿼리 시 top-k=5 유사 청크 반환
- data/ 없을 경우: 빈 DB로 시작, 법령 추가 시 자동 인덱싱

### 심의 노드 (`src/nodes/review.py`)
- 모델: `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`에 system 프롬프트 + 체크리스트 + 법령 주입
- 이미지 포함 시: `input_files`의 이미지를 동일 요청에 직접 포함 (분기 없음)
- 재심의 시 이전 eval_feedback을 메시지에 포함하여 개선 유도

### 평가자 노드 (`src/nodes/evaluator.py`)
- gemini-2.5-flash에 심의 결과 + 체크리스트 전달 -> JSON `{score, feedback}` 반환
- `loop_count` 증가, 임계값(80점) 미달 & 3회 미만이면 재심의
- 3회 초과 시 강제 종료 (현재 결과 그대로 반환)

### FastAPI (`src/main.py`)
- `POST /review` — multipart/form-data
  - fields: `input_text`, `channel`, `content_type`, `product_category`, `industry`, `language`
  - files: `input_files[]` (optional)
- `POST /ingest` — 법령 데이터 인덱싱 트리거 (data/ 디렉터리 경로 수신)
- 응답: `{review_result, eval_score, eval_feedback, law_list, checklist, loop_count}`

---

## requirements.txt 주요 패키지

```
langgraph>=0.2
langchain>=0.3
langchain-google-genai
langchain-postgres
google-generativeai
fastapi
uvicorn[standard]
python-multipart
pymupdf
python-docx
libhwp
psycopg2-binary
pgvector
```

---

## 환경 변수 (`.env.example`)

```
GEMINI_API_KEY=
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
LAW_DATA_DIR=../data/laws
EVAL_SCORE_THRESHOLD=80
MAX_LOOP_COUNT=3
```

---

## 구현 순서

1. `requirements.txt` + `.env.example` 생성
2. `src/state.py` — State TypedDict 정의
3. `src/vector_store/store.py` — ChromaDB 초기화
4. `src/nodes/ocr.py` — 파일 타입별 OCR
5. `src/nodes/rag.py` — 벡터 검색 노드
6. `src/nodes/checklist.py` — 체크리스트 생성
7. `src/nodes/review.py` — LLM/VLM 심의
8. `src/nodes/evaluator.py` — 평가자
9. `src/graph.py` — StateGraph 조립
10. `src/main.py` — FastAPI 엔드포인트

---

## 검증 방법

1. **단위**: 각 노드를 독립 호출하여 출력 확인
2. **통합 (텍스트)**: `POST /review`에 텍스트만 전송 -> 전체 파이프라인 확인
3. **통합 (파일)**: PDF/이미지 첨부 -> OCR -> RAG -> 심의 흐름 확인
4. **루프**: 낮은 임계값 설정 -> 재심의 루프 동작 확인
5. **루프 종료**: loop_count=3 도달 시 강제 종료 확인
