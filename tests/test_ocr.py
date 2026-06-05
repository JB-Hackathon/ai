from pathlib import Path
from unittest.mock import MagicMock, patch


FIXTURES = Path(__file__).parent / "fixtures"


# --- extract_docx ---


def test_extract_docx():
    from src.nodes.ocr.docx import extract_docx

    text = extract_docx(str(FIXTURES / "sample.docx"))
    assert "테스트" in text
    assert isinstance(text, str)


# --- extract_pdf (디지털) ---


def test_extract_pdf_digital():
    from src.nodes.ocr.pdf import extract_pdf

    text, is_visual = extract_pdf(str(FIXTURES / "digital.pdf"))
    assert isinstance(text, str)
    assert len(text.strip()) > 0
    assert is_visual is False


# --- extract_pdf (스캔) ---


def test_extract_pdf_scan():
    from src.nodes.ocr.pdf import extract_pdf

    # 첫 페이지 텍스트가 50자 미만인 PDF를 만들어 Gemini fallback 유도
    import fitz

    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((50, 100), "짧음")  # 50자 미만
        pdf.save(tmp_path)
        pdf.close()

        with patch(
            "src.nodes.ocr.pdf._gemini_vision", return_value="스캔 추출 결과"
        ) as mock_vision:
            text, is_visual = extract_pdf(tmp_path)

        mock_vision.assert_called_once()
        assert text == "스캔 추출 결과"
        assert is_visual is True
    finally:
        os.unlink(tmp_path)


# --- extract_image ---


def test_extract_image():
    from src.nodes.ocr.image import extract_image

    mock_response = MagicMock()
    mock_response.content = "이미지에서 추출된 텍스트"

    with patch("src.nodes.ocr.image.ChatGoogleGenerativeAI") as mock_llm_cls:
        mock_llm_cls.return_value.invoke.return_value = mock_response
        # PNG 픽스처가 없으므로 임시 파일 생성
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            tmp_path = tmp.name
        try:
            result = extract_image(tmp_path)
        finally:
            os.unlink(tmp_path)

    assert result == "이미지에서 추출된 텍스트"


# --- ocr_node ---


def test_ocr_node_no_files():
    from src.nodes.ocr import ocr_node

    assert ocr_node({}) == {}
    assert ocr_node({"input_files": []}) == {}


def test_ocr_node_docx():
    from src.nodes.ocr import ocr_node

    result = ocr_node({"input_files": [str(FIXTURES / "sample.docx")]})
    assert "ocr_text" in result
    assert result["needs_visual_review"] is False
    assert "테스트" in result["ocr_text"]


def test_ocr_node_image_sets_visual_review():
    from src.nodes.ocr import ocr_node

    mock_response = MagicMock()
    mock_response.content = "이미지 텍스트"

    with patch("src.nodes.ocr.image.ChatGoogleGenerativeAI") as mock_llm_cls:
        mock_llm_cls.return_value.invoke.return_value = mock_response
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            tmp_path = tmp.name
        try:
            result = ocr_node({"input_files": [tmp_path]})
        finally:
            os.unlink(tmp_path)

    assert result["needs_visual_review"] is True
    assert result["ocr_text"] == "이미지 텍스트"
