from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field


class ChecklistItem(BaseModel):
    item: str = Field(description="체크리스트 항목 (점검해야 할 구체적인 준수 기준)")
    reason: str = Field(description="이 항목이 해당 콘텐츠에 적용되는 이유")
    trigger_expression: str = Field(description="콘텐츠 내에서 이 기준을 촉발하는 표현 또는 내용")
    source_document: str = Field(description="근거가 된 법령명 또는 가이드라인 문서명")
    check_method: str = Field(description="심의 시 이 항목을 점검하는 방법")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="점검 우선순위: HIGH(법규 위반 가능성) / MEDIUM(누락 위험) / LOW(권고 사항)")
    uncertainty: str = Field(description="이 항목 적용의 불확실성 또는 조건부 판단 근거; 확실한 경우 빈 문자열")


class ChecklistOutput(BaseModel):
    items: list[ChecklistItem]
    conditional_items: list[ChecklistItem] = Field(
        default_factory=list,
        description="콘텐츠에 직접 적용되지 않지만 조건부로 검토가 필요한 항목",
    )


_SYSTEM = """\
너는 금융 콘텐츠 준법심의 체크리스트 생성기다.

## 역할
RAG로 검색된 참고문서에서 실제 콘텐츠에 적용 가능한 준법심의 기준을 추출하고,
적용 여부를 판단하여 체크리스트를 생성한다.

## 작업 순서
1. 검색된 참고문서에서 준법심의 기준 후보를 추출한다.
2. 각 기준 후보가 콘텐츠 원문에 적용되는지 판단한다.
   - 판단 기준: 콘텐츠 내에 해당 기준을 촉발하는 표현·상품 유형·채널 특성이 존재하는지 확인
3. 적용되는 기준만 items에 체크리스트로 만든다.
4. 직접 적용되지 않지만 조건부로 검토가 필요한 기준은 conditional_items로 분리한다.
5. 검색 근거가 없는 체크항목은 절대 만들지 않는다.

## 출력 제약
- 모든 items와 conditional_items는 반드시 source_document에 근거 문서명을 명시해야 한다.
- priority: HIGH(법규 위반 가능성) / MEDIUM(누락 위험) / LOW(권고 사항)
- 동일한 법령 조항에서 여러 기준이 나오면 각각 별도 item으로 분리한다.\
"""

_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _build_user_message(state: dict) -> str:
    product_category = state.get("product_category") or "해당 없음"

    parts = []
    if state.get("content_text"):
        parts.append(f"[사용자 입력 텍스트]\n{state['content_text']}")
    if state.get("ocr_text"):
        parts.append(f"[OCR 추출 텍스트]\n{state['ocr_text']}")
    combined_content = "\n\n".join(parts) if parts else "(없음)"

    law_text = "\n\n".join(state.get("law_list", [])) or "(없음)"

    return f"""\
## 사용자 입력 정보
- 광고 채널: {state.get("channel_type", "")}
- 콘텐츠 유형: {state.get("content_category", "")}
- 금융상품 범주: {product_category}
- 금융 업종: {state.get("business_sector", "")}
- 언어: {state.get("language_code", "")}

## 콘텐츠 원문 (텍스트 입력 + OCR 추출)
{combined_content}

## RAG 검색 참고문서
{law_text}\
"""


def _serialize_item(item: ChecklistItem, idx: int, conditional: bool = False) -> str:
    prefix = "[조건부] " if conditional else ""
    lines = [
        f"{prefix}[{idx}] {item.item}",
        f"  - 적용 이유: {item.reason}",
        f"  - 트리거 표현: {item.trigger_expression}",
        f"  - 근거 문서: {item.source_document}",
        f"  - 점검 방법: {item.check_method}",
        f"  - 우선순위: {item.priority}",
    ]
    if item.uncertainty:
        lines.append(f"  - 불확실성: {item.uncertainty}")
    return "\n".join(lines)


def checklist_node(state: dict) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    result: ChecklistOutput = llm.with_structured_output(ChecklistOutput).invoke(
        [
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=_build_user_message(state)),
        ]
    )

    sorted_items = sorted(result.items, key=lambda x: _PRIORITY_ORDER.get(x.priority, 3))
    sorted_conditional = sorted(result.conditional_items, key=lambda x: _PRIORITY_ORDER.get(x.priority, 3))

    return {
        "checklist": [_serialize_item(item, idx + 1) for idx, item in enumerate(sorted_items)],
        "conditional_checklist": [
            _serialize_item(item, idx + 1, conditional=True)
            for idx, item in enumerate(sorted_conditional)
        ],
    }
