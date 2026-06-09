from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from ..state import ChatState
from .tools import expression_edit, law_review

_tools = [law_review, expression_edit]


def _build_system(state: ChatState) -> str:
    law_text = "\n".join(state["law_list"])
    return f"""당신은 금융 광고 심의 전문가 챗봇입니다.
사용자가 1차 심의 결과를 검토하고 수정 요청하거나 질문할 수 있도록 도와주세요.

현재 심의 결과:
{state["review_result"]}

적용된 법령:
{law_text}"""


async def chatbot_node(state: ChatState) -> dict:
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools(_tools)
    system = SystemMessage(content=_build_system(state))
    response = await model.ainvoke([system] + state["messages"])
    return {"messages": [response]}
