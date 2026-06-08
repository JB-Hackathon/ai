from unittest.mock import MagicMock, patch

from src.nodes.checklist import ChecklistItem


def _make_item(item_text: str, priority: str = "HIGH") -> ChecklistItem:
    return ChecklistItem(
        item=item_text,
        reason="테스트 이유",
        trigger_expression="테스트 트리거",
        source_document="테스트 법령",
        check_method="테스트 점검 방법",
        priority=priority,
        uncertainty="",
    )


def test_checklist_node_returns_items():
    mock_result = MagicMock()
    mock_result.items = [_make_item("허위·과장 표현 없음"), _make_item("필수 고지 사항 포함", "MEDIUM")]
    mock_result.conditional_items = []

    with patch("src.nodes.checklist.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.with_structured_output.return_value.invoke.return_value = mock_result
        from src.nodes.checklist import checklist_node

        result = checklist_node({
            "content_text": "금융상품 광고 내용",
            "ocr_text": "추출된 텍스트",
            "law_list": ["자본시장법 제57조"],
        })

    assert len(result["checklist"]) == 2
    assert "허위·과장 표현 없음" in result["checklist"][0]
    assert result["conditional_checklist"] == []


def test_checklist_node_empty_inputs():
    mock_result = MagicMock()
    mock_result.items = [_make_item("기본 항목")]
    mock_result.conditional_items = []

    with patch("src.nodes.checklist.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.with_structured_output.return_value.invoke.return_value = mock_result
        from src.nodes.checklist import checklist_node

        result = checklist_node({})

    assert isinstance(result["checklist"], list)
    assert isinstance(result["conditional_checklist"], list)
