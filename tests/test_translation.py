import sys
from unittest.mock import MagicMock, patch


def _reload():
    sys.modules.pop("src.nodes.translation", None)


def test_korean_passthrough():
    _reload()
    with patch("src.nodes.translation.ChatGoogleGenerativeAI"):
        from src.nodes.translation import translation_node

        result = translation_node({"language_code": "ko", "content_text": "광고 문구", "ocr_text": "OCR 텍스트"})
    assert result == {}


def test_translates_content_text_only():
    _reload()
    mock_response = MagicMock()
    mock_response.content = "번역된 텍스트"

    with patch("src.nodes.translation.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.invoke.return_value = mock_response
        from src.nodes.translation import translation_node

        result = translation_node({
            "language_code": "en",
            "content_text": "Advertising copy",
            "ocr_text": "",
        })

    assert result["content_text"] == "번역된 텍스트"
    assert result["original_content_text"] == "Advertising copy"
    assert result["original_ocr_text"] == ""
    assert "ocr_text" not in result
    assert mock_cls.return_value.invoke.call_count == 1


def test_translates_both_fields():
    _reload()
    mock_response = MagicMock()
    mock_response.content = "번역됨"

    with patch("src.nodes.translation.ChatGoogleGenerativeAI") as mock_cls:
        mock_cls.return_value.invoke.return_value = mock_response
        from src.nodes.translation import translation_node

        result = translation_node({
            "language_code": "en",
            "content_text": "Content text",
            "ocr_text": "OCR text",
        })

    assert result["content_text"] == "번역됨"
    assert result["ocr_text"] == "번역됨"
    assert result["original_content_text"] == "Content text"
    assert result["original_ocr_text"] == "OCR text"
    assert mock_cls.return_value.invoke.call_count == 2


def test_empty_texts_no_translation_call():
    _reload()
    with patch("src.nodes.translation.ChatGoogleGenerativeAI") as mock_cls:
        from src.nodes.translation import translation_node

        result = translation_node({
            "language_code": "en",
            "content_text": "",
            "ocr_text": "",
        })

    assert result["original_content_text"] == ""
    assert result["original_ocr_text"] == ""
    assert "content_text" not in result
    assert "ocr_text" not in result
    mock_cls.return_value.invoke.assert_not_called()
