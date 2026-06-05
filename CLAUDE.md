# ai 개발 환경

## 가상환경 활성화

플랫폼: Windows + Git Bash

```bash
source venv/Scripts/activate
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

## 프로젝트 구조

```
src/
├── state.py          # ReviewState TypedDict (모든 노드 공유)
├── graph.py          # LangGraph StateGraph
├── main.py           # FastAPI 엔트리포인트
└── nodes/
    ├── ocr/          # 파일 → 텍스트 추출
    ├── rag.py        # 법령 검색 (현재 stub)
    ├── checklist.py  # 체크리스트 생성
    ├── review.py     # 심의 결과 작성
    └── evaluator.py  # 평가 및 루프 제어
```

상세 명세: `docs/1st/` 참고
