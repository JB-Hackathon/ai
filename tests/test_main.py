from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

_FORM = {
    "channel": "홈페이지",
    "content_type": "금융상품 광고",
    "industry": "은행",
    "language": "한국어",
}

_MOCK_STATE = {
    "review_result": "심의 결과서 내용",
    "eval_score": 90.0,
    "eval_feedback": "합격",
    "law_list": [],
    "checklist": ["항목1"],
    "loop_count": 1,
    "review_passed": True,
}


def test_post_review_missing_input_returns_422():
    from src.main import app

    client = TestClient(app)
    response = client.post("/review", data=_FORM)
    assert response.status_code == 422


def test_post_review_with_text_returns_200():
    with patch("src.main.graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=_MOCK_STATE)
        from src.main import app

        client = TestClient(app)
        response = client.post("/review", data={**_FORM, "input_text": "광고 내용"})

    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    assert data["review_result"] == "심의 결과서 내용"
    assert data["review_passed"] is True
    assert data["eval_score"] == 90.0
    assert data["loop_count"] == 1
