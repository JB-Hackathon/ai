import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

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


def _mock_chatbot_llm(responses: list):
    """chatbot_node의 ChatGoogleGenerativeAI를 모킹. bind_tools().ainvoke() 체인 처리."""
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(side_effect=responses)
    mock_cls = MagicMock()
    mock_cls.return_value.bind_tools.return_value = mock_model
    return mock_cls


def _mock_tool_llm(content: str):
    """tools.py의 ChatGoogleGenerativeAI를 모킹."""
    resp = MagicMock()
    resp.content = content
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=resp)
    return MagicMock(return_value=llm)


@pytest.mark.anyio
async def test_chatbot_general_response():
    ai_response = AIMessage(content="일반 응답입니다.")

    with patch("src.chatbot.nodes.chatbot.ChatGoogleGenerativeAI", _mock_chatbot_llm([ai_response])):
        from src.chatbot.graph import build_graph
        g = build_graph()
        result = await g.ainvoke(
            {**SAMPLE_STATE, "messages": [HumanMessage("질문입니다.")]},
            config={"configurable": {"thread_id": "test-general"}},
        )

    assert isinstance(result["messages"][-1], AIMessage)
    assert result["review_result"] == "기존 심의 결과"


@pytest.mark.anyio
async def test_chatbot_law_review_tool_call():
    ai_with_tool = AIMessage(
        content="",
        tool_calls=[{
            "name": "law_review",
            "args": {"user_instruction": "법령 누락됐어요"},
            "id": "call_law_001",
            "type": "tool_call",
        }],
    )
    ai_final = AIMessage(content="재작성 완료되었습니다.")

    with (
        patch("src.chatbot.nodes.chatbot.ChatGoogleGenerativeAI", _mock_chatbot_llm([ai_with_tool, ai_final])),
        patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", _mock_tool_llm("재작성된 심의 결과")),
    ):
        from src.chatbot.graph import build_graph
        g = build_graph()
        result = await g.ainvoke(
            {**SAMPLE_STATE, "messages": [HumanMessage("법령 누락됐어요")]},
            config={"configurable": {"thread_id": "test-law-review"}},
        )

    assert result["review_result"] == "재작성된 심의 결과"
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].tool_calls == []


@pytest.mark.anyio
async def test_chatbot_expression_edit_tool_call():
    ai_with_tool = AIMessage(
        content="",
        tool_calls=[{
            "name": "expression_edit",
            "args": {"user_instruction": "이 표현을 수정해주세요"},
            "id": "call_edit_001",
            "type": "tool_call",
        }],
    )
    ai_final = AIMessage(content="수정 완료되었습니다.")

    with (
        patch("src.chatbot.nodes.chatbot.ChatGoogleGenerativeAI", _mock_chatbot_llm([ai_with_tool, ai_final])),
        patch("src.chatbot.nodes.tools.ChatGoogleGenerativeAI", _mock_tool_llm("수정된 심의 결과")),
    ):
        from src.chatbot.graph import build_graph
        g = build_graph()
        result = await g.ainvoke(
            {**SAMPLE_STATE, "messages": [HumanMessage("이 표현을 수정해주세요")]},
            config={"configurable": {"thread_id": "test-expression-edit"}},
        )

    assert result["review_result"] == "수정된 심의 결과"
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].tool_calls == []


@pytest.mark.anyio
async def test_chatbot_graph_checkpointer_saves_state():
    mock_cls = _mock_chatbot_llm([AIMessage(content="응답1"), AIMessage(content="응답2")])

    with patch("src.chatbot.nodes.chatbot.ChatGoogleGenerativeAI", mock_cls):
        from src.chatbot.graph import build_graph
        g = build_graph()
        config = {"configurable": {"thread_id": "test-checkpoint"}}

        result1 = await g.ainvoke(
            {**SAMPLE_STATE, "messages": [HumanMessage("질문1")]},
            config=config,
        )
        result2 = await g.ainvoke(
            {**SAMPLE_STATE, "messages": [HumanMessage("질문2")]},
            config=config,
        )

    assert len(result2["messages"]) > len(result1["messages"])
