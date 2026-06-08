# ChatState 명세

## TypedDict 정의

```python
class ChatState(TypedDict):
    # Phase 1 체크포인터에서 주입 (읽기 전용 컨텍스트)
    review_result: str
    law_list: list[str]
    checklist: list[str]
    conditional_checklist: list[str]
    content_text: str
    ocr_text: str
    channel_type: str
    content_category: str
    product_category: str | None
    business_sector: str
    eval_score: float
    eval_feedback: str
    review_passed: bool
    needs_visual_review: bool

    # 챗봇 고유 필드
    messages: Annotated[list, add_messages]
```

---

## Phase 1 체크포인터에서 주입되는 필드

1차 심의 완료 후 `chat_threads.content_version_id`를 이용해 Phase 1 체크포인터에서 읽어온다.  
챗봇 실행 중에는 `review_result`를 제외하고 읽기 전용으로 사용한다.

| 필드 | 타입 | 출처 (Phase 1 노드) |
|------|------|---------------------|
| `review_result` | `str` | `review_node` — 심의 결과서 전문 (Tool 1·2가 갱신) |
| `law_list` | `list[str]` | `rag_node` — RAG로 선별된 법령 조항 목록 |
| `checklist` | `list[str]` | `checklist_node` — 심의 체크리스트 항목 |
| `conditional_checklist` | `list[str]` | `checklist_node` — 조건부 참고 체크리스트 |
| `content_text` | `str` | 원본 광고 텍스트 |
| `ocr_text` | `str` | OCR 추출 텍스트 |
| `channel_type` | `str` | 홈페이지 / SNS / 문자, 카카오톡 / 기타 |
| `content_category` | `str` | 금융상품 광고 / 업무광고 / 정보제공 / 기타 |
| `product_category` | `str \| None` | 상품군 (상품 광고인 경우만) |
| `business_sector` | `str` | 은행 / 여신금융 / 금융투자 / 저축은행 / 기타 |
| `eval_score` | `float` | 1차 평가 점수 (0~100) |
| `eval_feedback` | `str` | 1차 평가 피드백 |
| `review_passed` | `bool` | 심의 통과 여부 |
| `needs_visual_review` | `bool` | 이미지/스캔 PDF 포함 여부 |

---

## 챗봇 고유 필드

| 필드 | 타입 | 역할 |
|------|------|------|
| `messages` | `Annotated[list, add_messages]` | 대화 이력 (HumanMessage / AIMessage / ToolMessage). LangGraph `add_messages` 리듀서로 자동 누적 |

---

## 초기 State 설정

`main.py`의 `POST /thread/{thread_id}` 핸들러에서 Phase 1 체크포인터를 조회하여 구성한다.

```python
phase1_state = await phase1_graph.aget_state(
    {"configurable": {"thread_id": str(content_version_id)}}
)
v = phase1_state.values

initial_state: ChatState = {
    # Phase 1에서 주입
    "review_result": v["review_result"],
    "law_list": v["law_list"],
    "checklist": v["checklist"],
    "conditional_checklist": v["conditional_checklist"],
    "content_text": v["content_text"],
    "ocr_text": v["ocr_text"],
    "channel_type": v["channel_type"],
    "content_category": v["content_category"],
    "product_category": v.get("product_category"),
    "business_sector": v["business_sector"],
    "eval_score": v["eval_score"],
    "eval_feedback": v["eval_feedback"],
    "review_passed": v["review_passed"],
    "needs_visual_review": v["needs_visual_review"],
    # 챗봇 고유
    "messages": [HumanMessage(content=user_message)],
}
```
