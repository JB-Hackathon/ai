import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import ToolMessage

from src.chatbot.nodes.tools import expression_edit, law_review

SAMPLE_STATE = {
    "review_result": "기존 심의 결과",
    "law_list": ["자본시장법 제47조", "금융소비자보호법 제19조"],
    "checklist": ["허위 표현 없음"],
    "conditional_checklist": [],
    "content_text": "광고 텍스트",
    "ocr_text": "",
    "channel_type": "홈페이지",
    "content_category": "금융상품 광고",
    "product_category": None,
    "business_sector": "은행",
    "eval_score": 85.0,
    "eval_feedback": "",
    "review_passed": True,
    "needs_visual_review": False,
    "messages": [],
}


def _mock_llm(content: str):
    resp = MagicMock()
    resp.content = content
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=resp)
    return MagicMock(return_value=llm)


def _tool_call(tool_name: str, user_instruction: str, state: dict = SAMPLE_STATE, tid: str = "test-id"):
    return {
        "name": tool_name,
        "args": {"user_instruction": user_instruction, "state": state},
        "type": "tool_call",
        "id": tid,
    }


@pytest.mark.anyio
async def test_law_review_updates_review_result():
    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", _mock_llm("재작성된 심의 결과")):
        result = await law_review.ainvoke(_tool_call("law_review", "○○ 법령 누락"))

    assert result.update["review_result"] == "재작성된 심의 결과"


@pytest.mark.anyio
async def test_law_review_prompt_includes_law_list():
    captured = []

    async def fake_ainvoke(messages):
        captured.extend(messages)
        resp = MagicMock()
        resp.content = "결과"
        return resp

    mock_llm = MagicMock()
    mock_llm.ainvoke = fake_ainvoke

    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", MagicMock(return_value=mock_llm)):
        await law_review.ainvoke(_tool_call("law_review", "법령 확인"))

    body = str(captured)
    assert "자본시장법 제47조" in body
    assert "금융소비자보호법 제19조" in body


@pytest.mark.anyio
async def test_law_review_prompt_includes_user_instruction():
    captured = []

    async def fake_ainvoke(messages):
        captured.extend(messages)
        resp = MagicMock()
        resp.content = "결과"
        return resp

    mock_llm = MagicMock()
    mock_llm.ainvoke = fake_ainvoke

    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", MagicMock(return_value=mock_llm)):
        await law_review.ainvoke(_tool_call("law_review", "○○ 법령 누락됨"))

    assert "○○ 법령 누락됨" in str(captured)


@pytest.mark.anyio
async def test_law_review_returns_tool_message():
    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", _mock_llm("재작성된 결과")):
        result = await law_review.ainvoke(_tool_call("law_review", "법령 확인", tid="abc-xyz"))

    msgs = result.update["messages"]
    assert len(msgs) == 1
    assert isinstance(msgs[0], ToolMessage)
    assert msgs[0].tool_call_id == "abc-xyz"


@pytest.mark.anyio
async def test_expression_edit_updates_review_result():
    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", _mock_llm("수정된 심의 결과")):
        result = await expression_edit.ainvoke(_tool_call("expression_edit", "이 표현을 수정해줘"))

    assert result.update["review_result"] == "수정된 심의 결과"


@pytest.mark.anyio
async def test_expression_edit_prompt_includes_current_result():
    captured = []

    async def fake_ainvoke(messages):
        captured.extend(messages)
        resp = MagicMock()
        resp.content = "수정된 결과"
        return resp

    mock_llm = MagicMock()
    mock_llm.ainvoke = fake_ainvoke

    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", MagicMock(return_value=mock_llm)):
        await expression_edit.ainvoke(_tool_call("expression_edit", "표현 수정"))

    assert "기존 심의 결과" in str(captured)


@pytest.mark.anyio
async def test_expression_edit_prompt_excludes_law_list():
    captured = []

    async def fake_ainvoke(messages):
        captured.extend(messages)
        resp = MagicMock()
        resp.content = "수정된 결과"
        return resp

    mock_llm = MagicMock()
    mock_llm.ainvoke = fake_ainvoke

    with patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", MagicMock(return_value=mock_llm)):
        await expression_edit.ainvoke(_tool_call("expression_edit", "표현 수정"))

    body = str(captured)
    assert "자본시장법 제47조" not in body
    assert "금융소비자보호법 제19조" not in body
