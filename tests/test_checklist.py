from unittest.mock import MagicMock, patch


def test_checklist_node_returns_items():
    mock_result = MagicMock()
    mock_result.items = ["허위·과장 표현 없음", "필수 고지 사항 포함"]

    with patch("src.nodes.checklist.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.with_structured_output.return_value.invoke.return_value = mock_result
        from src.nodes.checklist import checklist_node

        result = checklist_node({
            "input_text": "금융상품 광고 내용",
            "ocr_text": "추출된 텍스트",
            "law_list": ["자본시장법 제57조"],
        })

    assert result["checklist"] == ["허위·과장 표현 없음", "필수 고지 사항 포함"]


def test_checklist_node_empty_inputs():
    mock_result = MagicMock()
    mock_result.items = ["기본 항목"]

    with patch("src.nodes.checklist.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.with_structured_output.return_value.invoke.return_value = mock_result
        from src.nodes.checklist import checklist_node

        result = checklist_node({})

    assert isinstance(result["checklist"], list)
