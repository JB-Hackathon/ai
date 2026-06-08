# AI Service — 금융 콘텐츠 준법 심의

금융 광고·콘텐츠에 대한 준법 심의를 자동화하는 API 서비스.  
OCR → 번역 → RAG → 체크리스트 → 심의 → 평가 파이프라인을 LangGraph로 실행하며, 기준 미달 시 최대 3회 자동 재심의한다.

## 기술 스택

| 항목 | 기술 |
|------|------|
| LLM/VLM | Google Gemini 2.5 Flash |
| 오케스트레이션 | LangGraph (StateGraph) |
| 벡터 검색 | PostgreSQL + pgvector |
| API | FastAPI |
| 체크포인트 | AsyncPostgresSaver (PostgreSQL) |
| 문서 처리 | PyMuPDF, Gemini Vision, python-docx, libhwp |

## 빠른 시작

```bash
source venv/bin/activate
cp .env.example .env          # GEMINI_API_KEY, DATABASE_URL 입력
pip install -r requirements.txt
uvicorn main:app --reload
```

## API

```http
POST /review/{content_version_id}
```

DB의 `review_content_versions` 테이블에서 콘텐츠를 조회한 뒤 심의를 실행한다.

**응답 필드:** `eval_score`, `review_result`, `checklist`, `law_list`, `eval_feedback`, `review_status`

```http
GET /ping
```

## 개발

```bash
source venv/bin/activate
ruff check src/ tests/   # 린트
ruff format src/ tests/  # 포맷
pytest tests/            # 테스트
```

## 프로젝트 구조

```
src/
├── state.py          # ReviewState TypedDict
├── graph.py          # LangGraph StateGraph 조립
├── main.py           # FastAPI 엔트리포인트
└── nodes/
    ├── ocr/          # 파일 → 텍스트 (PDF/이미지/DOCX/HWP)
    ├── translation.py # 외국어 → 한국어
    ├── rag.py         # 법령 하이브리드 검색
    ├── checklist.py   # 체크리스트 생성
    ├── review.py      # 심의 결과서 작성
    └── evaluator.py   # 평가 및 루프 제어
```

## 상세 문서

| 문서 | 내용 |
|------|------|
| [docs/1st/overview.md](docs/1st/overview.md) | 전체 개요 및 처리 흐름 |
| [docs/1st/setup.md](docs/1st/setup.md) | 환경 설정 및 실행 |
| [docs/1st/api.md](docs/1st/api.md) | API 엔드포인트 상세 |
| [docs/1st/graph.md](docs/1st/graph.md) | LangGraph 워크플로우 |
| [docs/1st/state.md](docs/1st/state.md) | ReviewState 필드 명세 |
| [docs/1st/memory.md](docs/1st/memory.md) | 체크포인트·메모리 구조 |
