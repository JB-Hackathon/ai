from src.nodes.rag import rag_node


def test_rag_returns_empty_law_list():
    result = rag_node({"input_text": "광고 내용"})
    assert result["law_list"] == []


def test_rag_passes_needs_visual_review_true():
    result = rag_node({"needs_visual_review": True})
    assert result["needs_visual_review"] is True


def test_rag_passes_needs_visual_review_false():
    result = rag_node({"needs_visual_review": False})
    assert result["needs_visual_review"] is False


def test_rag_defaults_needs_visual_review_to_false():
    result = rag_node({})
    assert result["needs_visual_review"] is False
