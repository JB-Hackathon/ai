import os
import tempfile
from unittest.mock import MagicMock, patch


def _make_mock_llm(content: str):
    mock_resp = MagicMock()
    mock_resp.content = content
    mock_cls = MagicMock()
    mock_cls.return_value.invoke.return_value = mock_resp
    return mock_cls


def test_review_node_text_only():
    with patch("src.nodes.review.ChatGoogleGenerativeAI", _make_mock_llm("심의 결과서")):
        from src.nodes.review import review_node

        result = review_node({
            "input_text": "금융상품 광고",
            "ocr_text": "",
            "checklist": ["허위 표현 없음"],
            "law_list": [],
            "needs_visual_review": False,
            "eval_feedback": "",
        })

    assert result["review_result"] == "심의 결과서"


def test_review_node_includes_feedback_on_retry():
    captured_prompts = []

    def fake_invoke(messages):
        captured_prompts.append(str(messages))
        resp = MagicMock()
        resp.content = "개선된 심의 결과"
        return resp

    mock_cls = MagicMock()
    mock_cls.return_value.invoke.side_effect = fake_invoke

    with patch("src.nodes.review.ChatGoogleGenerativeAI", mock_cls):
        from src.nodes.review import review_node

        review_node({
            "input_text": "광고",
            "ocr_text": "",
            "checklist": [],
            "law_list": [],
            "needs_visual_review": False,
            "eval_feedback": "이전 피드백 내용",
        })

    assert "이전 피드백 내용" in captured_prompts[0]


def test_review_node_with_image():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        tmp_path = tmp.name

    captured_messages = []

    def fake_invoke(messages):
        captured_messages.extend(messages)
        resp = MagicMock()
        resp.content = "이미지 포함 심의 결과"
        return resp

    mock_cls = MagicMock()
    mock_cls.return_value.invoke.side_effect = fake_invoke

    try:
        with patch("src.nodes.review.ChatGoogleGenerativeAI", mock_cls):
            from src.nodes.review import review_node

            result = review_node({
                "input_text": "광고",
                "ocr_text": "",
                "checklist": [],
                "law_list": [],
                "needs_visual_review": True,
                "input_files": [tmp_path],
                "eval_feedback": "",
            })
    finally:
        os.unlink(tmp_path)

    assert result["review_result"] == "이미지 포함 심의 결과"
    # HumanMessage content에 image_url 블록이 포함되어야 함
    human_msg = captured_messages[1]
    image_blocks = [c for c in human_msg.content if isinstance(c, dict) and c.get("type") == "image_url"]
    assert len(image_blocks) == 1
