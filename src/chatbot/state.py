from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    # Phase 1 체크포인터에서 주입 (review_result만 Tool이 갱신, 나머지 읽기 전용)
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

    # 챗봇 고유
    messages: Annotated[list, add_messages]
