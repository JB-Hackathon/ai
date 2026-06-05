from unittest.mock import MagicMock, patch


def _mock_eval(score: float, feedback: str):
    mock_result = MagicMock()
    mock_result.score = score
    mock_result.feedback = feedback
    mock_cls = MagicMock()
    mock_cls.return_value.with_structured_output.return_value.invoke.return_value = mock_result
    return mock_cls


def test_evaluator_passed_when_score_gte_80():
    with patch("src.nodes.evaluator.ChatGoogleGenerativeAI", _mock_eval(90.0, "훌륭합니다")):
        from src.nodes.evaluator import evaluator_node

        result = evaluator_node({"loop_count": 0, "review_result": "심의 결과", "checklist": [], "law_list": []})

    assert result["review_passed"] is True
    assert result["eval_score"] == 90.0


def test_evaluator_not_passed_when_score_lt_80():
    with patch("src.nodes.evaluator.ChatGoogleGenerativeAI", _mock_eval(60.0, "개선 필요")):
        from src.nodes.evaluator import evaluator_node

        result = evaluator_node({"loop_count": 0, "review_result": "심의 결과", "checklist": [], "law_list": []})

    assert result["review_passed"] is False
    assert result["eval_feedback"] == "개선 필요"


def test_evaluator_increments_loop_count():
    with patch("src.nodes.evaluator.ChatGoogleGenerativeAI", _mock_eval(70.0, "피드백")):
        from src.nodes.evaluator import evaluator_node

        result = evaluator_node({"loop_count": 1, "review_result": "", "checklist": [], "law_list": []})

    assert result["loop_count"] == 2


def test_evaluator_loop_count_starts_from_zero():
    with patch("src.nodes.evaluator.ChatGoogleGenerativeAI", _mock_eval(85.0, "좋음")):
        from src.nodes.evaluator import evaluator_node

        result = evaluator_node({"loop_count": 0, "review_result": "", "checklist": [], "law_list": []})

    assert result["loop_count"] == 1
