from unittest.mock import MagicMock, patch


_BASE_STATE = {
    "input_text": "금융상품 광고 내용",
    "input_files": [],
    "channel": "홈페이지",
    "content_type": "금융상품 광고",
    "product_category": None,
    "industry": "은행",
    "language": "한국어",
    "ocr_text": "",
    "law_list": [],
    "checklist": [],
    "needs_visual_review": False,
    "review_result": "",
    "eval_score": 0.0,
    "eval_feedback": "",
    "loop_count": 0,
    "review_passed": False,
    "messages": [],
}


def _setup_mocks(checklist_items, review_content, eval_score, eval_feedback):
    """checklist / review / evaluator LLM을 mock 설정한 tuple 반환."""
    # checklist mock
    checklist_result = MagicMock()
    checklist_result.items = checklist_items
    mock_checklist = MagicMock()
    mock_checklist.return_value.with_structured_output.return_value.invoke.return_value = checklist_result

    # review mock
    review_resp = MagicMock()
    review_resp.content = review_content
    mock_review = MagicMock()
    mock_review.return_value.invoke.return_value = review_resp

    # evaluator mock
    eval_result = MagicMock()
    eval_result.score = eval_score
    eval_result.feedback = eval_feedback
    mock_eval = MagicMock()
    mock_eval.return_value.with_structured_output.return_value.invoke.return_value = eval_result

    return mock_checklist, mock_review, mock_eval


def test_graph_passes_on_high_score():
    mock_checklist, mock_review, mock_eval = _setup_mocks(
        checklist_items=["항목1"],
        review_content="심의 결과서",
        eval_score=90.0,
        eval_feedback="합격",
    )

    with (
        patch("src.nodes.checklist.ChatGoogleGenerativeAI", mock_checklist),
        patch("src.nodes.review.ChatGoogleGenerativeAI", mock_review),
        patch("src.nodes.evaluator.ChatGoogleGenerativeAI", mock_eval),
    ):
        from src.graph import graph

        result = graph.invoke(_BASE_STATE, config={"configurable": {"thread_id": "test-pass"}})

    assert result["review_passed"] is True
    assert result["loop_count"] == 1
    assert result["checklist"] == ["항목1"]


def test_graph_ends_after_max_loops():
    mock_checklist, mock_review, mock_eval = _setup_mocks(
        checklist_items=["항목1"],
        review_content="심의 결과서",
        eval_score=50.0,  # 항상 미달
        eval_feedback="개선 필요",
    )

    with (
        patch("src.nodes.checklist.ChatGoogleGenerativeAI", mock_checklist),
        patch("src.nodes.review.ChatGoogleGenerativeAI", mock_review),
        patch("src.nodes.evaluator.ChatGoogleGenerativeAI", mock_eval),
    ):
        from src.graph import graph

        result = graph.invoke(_BASE_STATE, config={"configurable": {"thread_id": "test-loop"}})

    assert result["loop_count"] == 3
    assert result["review_passed"] is False
