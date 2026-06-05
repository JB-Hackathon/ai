from src.state import ReviewState

EXPECTED_FIELDS = {
    "input_text",
    "input_files",
    "channel",
    "content_type",
    "product_category",
    "industry",
    "language",
    "ocr_text",
    "law_list",
    "checklist",
    "needs_visual_review",
    "review_result",
    "eval_score",
    "eval_feedback",
    "loop_count",
    "review_passed",
    "messages",
}


def test_review_state_fields():
    assert EXPECTED_FIELDS == ReviewState.__annotations__.keys()
