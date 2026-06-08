from src.chatbot.state import ChatState

EXPECTED_FIELDS = {
    "review_result", "law_list", "checklist", "conditional_checklist",
    "content_text", "ocr_text", "channel_type", "content_category",
    "product_category", "business_sector", "eval_score", "eval_feedback",
    "review_passed", "needs_visual_review",
    "messages",
}


def test_chat_state_fields():
    assert EXPECTED_FIELDS == ChatState.__annotations__.keys()
