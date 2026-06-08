from src.state import ReviewState

EXPECTED_FIELDS = {
    "content_text",
    "content_file_path",
    "channel_type",
    "content_category",
    "product_category",
    "business_sector",
    "language_code",
    "ocr_text",
    "law_list",
    "checklist",
    "conditional_checklist",
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
