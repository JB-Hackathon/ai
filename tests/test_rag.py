from unittest.mock import patch

from src.nodes.rag import _LawChunk, _SearchQuery, _merge_chunks, rag_node


def _make_queries(*queries: str) -> list[_SearchQuery]:
    return [_SearchQuery(query=q, intent="테스트") for q in queries]


def _make_chunk(title: str = "테스트법", text: str = "내용") -> _LawChunk:
    return _LawChunk(title=title, issuing_authority="금융위원회", chunk_text=text)


# ── rag_node ──────────────────────────────────────────────────────────────────


def test_rag_returns_empty_law_list_when_no_queries():
    with patch("src.nodes.rag._generate_search_queries", return_value=[]):
        result = rag_node({})
    assert result["law_list"] == []


def test_rag_searches_once_per_query():
    chunk = _make_chunk()
    with (
        patch("src.nodes.rag._generate_search_queries", return_value=_make_queries("쿼리1", "쿼리2")),
        patch("src.nodes.rag._embed_query", return_value=[0.0] * 1024),
        patch("src.nodes.rag._search_laws", return_value=[chunk]) as mock_search,
    ):
        rag_node({"content_text": "테스트"})
    assert mock_search.call_count == 2


def test_rag_deduplicates_chunks():
    dup = _make_chunk("중복법", "같은 내용")
    with (
        patch("src.nodes.rag._generate_search_queries", return_value=_make_queries("q1", "q2")),
        patch("src.nodes.rag._embed_query", return_value=[0.0] * 1024),
        patch("src.nodes.rag._search_laws", return_value=[dup]),
    ):
        result = rag_node({"content_text": "테스트"})
    assert len(result["law_list"]) == 1


def test_rag_passes_needs_visual_review_true():
    with patch("src.nodes.rag._generate_search_queries", return_value=[]):
        result = rag_node({"needs_visual_review": True})
    assert result["needs_visual_review"] is True


def test_rag_passes_needs_visual_review_false():
    with patch("src.nodes.rag._generate_search_queries", return_value=[]):
        result = rag_node({"needs_visual_review": False})
    assert result["needs_visual_review"] is False


def test_rag_defaults_needs_visual_review_to_false():
    with patch("src.nodes.rag._generate_search_queries", return_value=[]):
        result = rag_node({})
    assert result["needs_visual_review"] is False


# ── _merge_chunks ─────────────────────────────────────────────────────────────


def test_merge_chunks_deduplicates():
    c1 = _make_chunk("법A", "내용1")
    c2 = _make_chunk("법A", "내용1")  # 중복
    c3 = _make_chunk("법B", "내용2")
    merged = _merge_chunks([[c1, c3], [c2]])
    assert len(merged) == 2
    assert merged[0].title == "법A"
    assert merged[1].title == "법B"


def test_merge_chunks_preserves_first_query_order():
    c1 = _make_chunk("법A", "내용1")
    c2 = _make_chunk("법B", "내용2")
    c3 = _make_chunk("법C", "내용3")
    merged = _merge_chunks([[c1, c2], [c3]])
    assert [c.title for c in merged] == ["법A", "법B", "법C"]


def test_merge_chunks_respects_final_top_k():
    with patch("src.nodes.rag._FINAL_TOP_K", 2):
        chunks = [_make_chunk(f"법{i}", f"내용{i}") for i in range(5)]
        merged = _merge_chunks([chunks])
    assert len(merged) == 2


# ── _generate_search_queries fallback ────────────────────────────────────────


def test_generate_search_queries_fallback_on_llm_error():
    from src.nodes.rag import _generate_search_queries

    with patch("langchain_google_genai.ChatGoogleGenerativeAI", side_effect=Exception("API 오류")):
        result = _generate_search_queries({"content_text": "테스트 광고"})
    assert len(result) == 1
    assert result[0].query == "테스트 광고"


def test_generate_search_queries_fallback_empty_on_no_content():
    from src.nodes.rag import _generate_search_queries

    with patch("langchain_google_genai.ChatGoogleGenerativeAI", side_effect=Exception("API 오류")):
        result = _generate_search_queries({})
    assert result == []
