# ai 개발 환경

## 가상환경 활성화

```bash
source venv/bin/activate
```

> `ruff: command not found` 오류가 나면 venv가 활성화되지 않은 것이다.

## 개발 명령어

모든 명령은 `ai/` 디렉토리 기준으로 실행한다.

```bash
ruff check src/ tests/   # 린트
ruff format src/ tests/  # 포맷
pytest tests/            # 테스트
```

각 Unit 완성 후 `ruff check` → `pytest` 순서로 반드시 실행한다.

## 워크플로우 개요

### 1차 심의 워크플로우 (`src/`)

파일 업로드 → OCR → 번역 → 법령 검색(RAG) → 체크리스트 생성 → 심의 결과 작성 → 평가/루프

엔드포인트: `POST /review/{content_version_id}`  
상세 명세: `docs/1st/`

### 챗봇 워크플로우 (`src/chatbot/`)

1차 심의 완료 후, 사용자가 결과를 수정 요청하거나 질문하는 대화형 인터페이스

- 의도 분석 → Tool 호출 없으면 일반 응답
- Tool 1: 누락 법령 재검토 (기존 `law_list` 기반 심의 재작성)
- Tool 2: 표현 수정

엔드포인트: `POST /thread/{thread_id}`  
상세 명세: `docs/chatbot/`

## 프로젝트 구조

```
main.py               # FastAPI 엔트리포인트
run_graph.py          # 1차 심의 그래프 CLI 테스트 도구

src/
├── state.py          # ReviewState TypedDict (1차 심의 노드 공유)
├── graph.py          # LangGraph StateGraph (1차 심의)
├── nodes/
│   ├── ocr/          # 파일 → 텍스트 추출 (pdf, docx, hwp, image)
│   ├── rag.py        # 법령 검색 (pgvector 하이브리드 검색)
│   ├── checklist.py  # 체크리스트 생성
│   ├── review.py     # 심의 결과 작성
│   ├── evaluator.py  # 평가 및 루프 제어
│   └── translation.py# 다국어 번역
└── chatbot/
    ├── state.py      # ChatState TypedDict (챗봇 노드 공유)
    ├── graph.py      # LangGraph StateGraph (챗봇)
    └── nodes/
        ├── intent.py           # 의도 분석 및 라우팅
        ├── general_response.py # 일반 응답
        ├── law_review.py       # Tool 1: 법령 재검토
        └── expression_edit.py  # Tool 2: 표현 수정

tests/
├── test_*.py         # 1차 심의 노드 단위 테스트
└── chatbot/
    └── test_*.py     # 챗봇 노드 단위 테스트 + 통합 테스트

docs/
├── 1st/              # 1차 심의 워크플로우 상세 명세
└── chatbot/          # 챗봇 워크플로우 상세 명세
```
