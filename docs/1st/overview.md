# 1차 심의 워크플로우 개요

## 목적

금융 광고/콘텐츠에 대한 준법 자문 AI 시스템.
사용자가 제출한 텍스트 또는 파일(이미지/PDF/DOCX/HWP)을 분석하고,
관련 법령을 RAG로 선별하여 LLM/VLM 기반 심의를 수행한다.
심의 결과는 내부 평가자가 검증하며, 기준 미달 시 최대 3회 재심의한다.
FastAPI 서버로 노출하여 backend와 연동한다.

## 기술 스택

| 역할 | 기술 |
|------|------|
| LLM/VLM | gemini-2.5-flash (Google) — 텍스트 + 이미지 통합 처리 |
| OCR | PyMuPDF(PDF 텍스트/스캔 감지), Gemini Vision(이미지/스캔PDF), python-docx(DOCX), libhwp(HWP) |
| 벡터 스토어 | PostgreSQL + pgvector + gemini-embedding-2 (1024차원) |
| RAG 데이터 | `data/` 서브모듈에서 제공 예정 (인덱싱 파이프라인 포함) |
| 서비스 | FastAPI REST API |

## 코드 디렉터리 구조

```
ai/
├── src/
│   ├── main.py              # FastAPI 앱 엔트리포인트
│   ├── state.py             # LangGraph State (TypedDict)
│   ├── graph.py             # LangGraph StateGraph 조립
│   ├── nodes/
│   │   ├── ocr/             # OCR 노드 (파일 -> 텍스트)
│   │   │   ├── __init__.py  # ocr_node 함수 (확장자 → 핸들러 디스패치)
│   │   │   ├── pdf.py       # extract_pdf()
│   │   │   ├── docx.py      # extract_docx()
│   │   │   ├── hwp.py       # extract_hwp()
│   │   │   └── image.py     # extract_image()
│   │   ├── translation.py   # 번역 노드 (외국어 → 한국어)
│   │   ├── rag.py           # RAG 노드 (법령 선별)
│   │   ├── checklist.py     # 체크리스트 생성 노드
│   │   ├── review.py        # 심의 노드 (LLM / VLM 분기)
│   │   └── evaluator.py     # 평가자 노드
├── requirements.txt
└── .env.example
```

## 구현 순서

1. `requirements.txt` + `.env.example` 생성
2. `src/state.py` — State TypedDict 정의
3. `src/nodes/ocr/` — 파일 타입별 OCR
4. `src/nodes/translation.py` — 번역 노드
5. `src/nodes/rag.py` — 하이브리드 법령 검색 노드
6. `src/nodes/checklist.py` — 체크리스트 생성
7. `src/nodes/review.py` — LLM/VLM 심의
8. `src/nodes/evaluator.py` — 평가자
9. `src/graph.py` — StateGraph 조립
10. `src/main.py` — FastAPI 엔드포인트

## 검증 방법

1. **단위**: 각 노드를 독립 호출하여 출력 확인
2. **통합 (텍스트)**: `POST /review`에 텍스트만 전송 → 전체 파이프라인 확인
3. **통합 (파일)**: PDF/이미지 첨부 → OCR → RAG → 심의 흐름 확인
4. **루프**: 낮은 임계값 설정 → 재심의 루프 동작 확인
5. **루프 종료**: loop_count=3 도달 시 강제 종료 확인
