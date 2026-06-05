# ReviewState 명세

## TypedDict 정의

```python
class ReviewState(TypedDict):
    # 사용자 입력 (요청 시 채워짐)
    input_text: str
    input_files: list[str]         # 파일 경로 목록
    channel: str
    content_type: str
    product_category: str | None
    industry: str
    language: str

    # Agent 실행 중 채워지는 필드
    ocr_text: str                  # OCR 추출 텍스트
    law_list: list[str]            # RAG로 찾은 법령 조항
    checklist: list[str]           # LLM이 생성한 심의 체크리스트
    needs_visual_review: bool      # rag_node가 시각 요건 법령 감지 시 True
    review_result: str             # 심의 결과서 (초안)
    eval_score: float              # 평가 점수 (0~100)
    eval_feedback: str             # 평가 피드백
    loop_count: int                # 재심의 횟수 (무한 루프 방지)
    review_passed: bool            # 심의 기준 충족 여부 (score>=80이면 True, 강제 종료 시 False)
    messages: Annotated[list, add_messages]  # 대화 로그 (LangGraph add_messages reducer)
```

## 사용자 입력 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `input_text` | `str` | 사용자가 최초로 제출한 원본 글이나 광고 문구 |
| `input_files` | `list[str]` | 이미지 / PDF / DOCX / HWP 파일 경로 목록 |
| `channel` | `str` | 홈페이지 / SNS / 문자, 카카오톡 / 기타 |
| `content_type` | `str` | 금융상품 광고 / 업무광고 / 정보제공 / 기타 |
| `product_category` | `str \| None` | 예금성 / 대출성 / 카드·혜택 / 자동차금융 / 투자성 / 예금자보호 / 기타 (상품 광고인 경우만) |
| `industry` | `str` | 은행 / 여신금융 / 금융투자 / 저축은행 / 기타 |
| `language` | `str` | 한국어 / 영어 / 필리핀어 / 캄보디아어 / 중국어 / 베트남어 |

## Agent 실행 중 채워지는 필드

| 필드 | 타입 | 설명 | 담당 노드 |
|------|------|------|-----------|
| `ocr_text` | `str` | OCR 추출 텍스트 | `ocr_node` |
| `needs_visual_review` | `bool` | Vision OCR 사용 여부 (이미지/스캔PDF 감지) | `ocr_node` → `rag_node` 보완 |
| `law_list` | `list[str]` | RAG로 찾은 법령 조항 | `rag_node` |
| `checklist` | `list[str]` | 심의 체크리스트 | `checklist_node` |
| `review_result` | `str` | 심의 결과서 초안 | `review_node` |
| `eval_score` | `float` | 평가 점수 (0~100) | `evaluator_node` |
| `eval_feedback` | `str` | 평가 피드백 | `evaluator_node` |
| `loop_count` | `int` | 재심의 횟수 — **초기값 0**, `evaluator_node`에서 매 실행 시 +1 | `evaluator_node` |
| `review_passed` | `bool` | 심의 기준 충족 여부 | `evaluator_node` |
| `messages` | `Annotated[list, add_messages]` | 워크플로우 내 대화 로그 | 전 노드 |

## 초기 State 설정

`main.py`에서 그래프 호출 전 아래와 같이 초기화한다. 실행 중 채워지는 필드는 코드에서 `.get("field", default)` 패턴으로 접근한다.

```python
initial_state = {
    "input_text": input_text or "",
    "input_files": saved_file_paths,
    "channel": channel,
    "content_type": content_type,
    "product_category": product_category,
    "industry": industry,
    "language": language,
    # 실행 중 채워지는 필드 초기값
    "ocr_text": "",
    "needs_visual_review": False,
    "law_list": [],
    "checklist": [],
    "review_result": "",
    "eval_score": 0.0,
    "eval_feedback": "",
    "loop_count": 0,
    "review_passed": False,
    "messages": [],
}
```
