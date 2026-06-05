from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ReviewState(TypedDict):
    # 사용자 입력
    input_text: str
    input_files: list[str]
    channel: str
    content_type: str
    product_category: str | None
    industry: str
    language: str

    # 실행 중 채워지는 필드
    ocr_text: str
    law_list: list[str]
    checklist: list[str]
    needs_visual_review: bool
    review_result: str
    eval_score: float
    eval_feedback: str
    loop_count: int
    review_passed: bool
    messages: Annotated[list, add_messages]
