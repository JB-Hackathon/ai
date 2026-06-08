from typing import Annotated

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

_LAW_REVIEW_SYSTEM = "당신은 금융 광고 심의 전문가입니다. 체크리스트와 법령을 기반으로 심의 결과서를 작성해주세요."
_EXPRESSION_EDIT_SYSTEM = "당신은 금융 광고 심의 전문가입니다. 사용자가 요청한 특정 표현만 수정하여 심의 결과서를 반환해주세요. 수정 범위 외의 내용은 그대로 유지하세요."


@tool
async def law_review(
    user_instruction: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """법령이 누락된 경우, 기존 law_list 전체를 반영해 심의 결과를 재작성합니다."""
    checklist_text = "\n".join(f"- {item}" for item in state["checklist"])
    law_text = "\n".join(state["law_list"])
    conditional_text = "\n".join(f"- {item}" for item in state["conditional_checklist"])

    body = f"""## 심의 대상 텍스트
{state["content_text"]}

## OCR 추출 텍스트
{state["ocr_text"]}

## 체크리스트
{checklist_text}

## 관련 법령 (전체 목록)
{law_text}
"""
    if conditional_text:
        body += f"\n## 조건부 참고항목 (직접 적용 기준은 아니나 맥락 참고용)\n{conditional_text}"
    body += f"\n## 사용자 지적 사항\n{user_instruction}"
    body += "\n\n위 내용을 바탕으로 법령을 빠짐없이 반영하여 심의 결과서를 재작성해주세요."

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    response = await llm.ainvoke([SystemMessage(content=_LAW_REVIEW_SYSTEM), HumanMessage(content=body)])
    new_result = response.content
    return Command(update={
        "review_result": new_result,
        "messages": [ToolMessage(content=new_result, tool_call_id=tool_call_id)],
    })


@tool
async def expression_edit(
    user_instruction: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """1차 심의 결과에서 특정 표현·문구만 수정합니다."""
    body = f"""## 현재 심의 결과서
{state["review_result"]}

## 수정 요청
{user_instruction}

요청된 표현·문구만 수정하여 심의 결과서를 반환해주세요. 수정 범위 외의 내용은 그대로 유지하세요."""

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    response = await llm.ainvoke([SystemMessage(content=_EXPRESSION_EDIT_SYSTEM), HumanMessage(content=body)])
    new_result = response.content
    return Command(update={
        "review_result": new_result,
        "messages": [ToolMessage(content=new_result, tool_call_id=tool_call_id)],
    })
