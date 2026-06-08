# 번역 노드

## 역할

`language_code`가 `"한국어"`가 아닌 경우, `content_text`와 `ocr_text`를 한국어로 번역한다.
원본 텍스트는 `original_content_text` / `original_ocr_text`에 백업하고,
`content_text` / `ocr_text`를 번역 결과로 교체하여 하위 노드(RAG·체크리스트·심의)가
별도 분기 없이 동일한 필드를 사용할 수 있게 한다.

## 동작 조건

| 조건 | 동작 |
|------|------|
| `language_code == "한국어"` | 아무것도 변경하지 않음 (pass-through) |
| `language_code != "한국어"` | 비어 있지 않은 필드만 번역, 원본 백업 |

## State 변경

| 필드 | 동작 |
|------|------|
| `original_content_text` | `content_text` 원본 백업 |
| `original_ocr_text` | `ocr_text` 원본 백업 |
| `content_text` | 번역된 한국어 텍스트로 교체 (원본이 비어 있으면 변경 없음) |
| `ocr_text` | 번역된 한국어 텍스트로 교체 (원본이 비어 있으면 변경 없음) |

## LLM 설정

- 모델: `gemini-2.5-flash`
- 입력: 번역 대상 텍스트 + 원문 언어(`language_code`)
- 출력: 한국어 번역 결과 (plain str)

## 프롬프트 지침

- 원문에 충실한 직역 (의역 최소화)
- 수치·금리·상품명은 원문을 괄호 안에 병기 (예: `3% 이자율(3% interest rate)`)
- 번역만 수행하며 심의 의견·평가·수정 제안을 추가하지 말 것

## 구현 위치

`src/nodes/translation.py`

## 의사 코드

```python
def translation_node(state: ReviewState) -> dict:
    if state.get("language_code") == "한국어":
        return {}  # pass-through

    updates = {
        "original_content_text": state.get("content_text", ""),
        "original_ocr_text": state.get("ocr_text", ""),
    }
    if state.get("content_text"):
        updates["content_text"] = _translate(state["content_text"], state["language_code"])
    if state.get("ocr_text"):
        updates["ocr_text"] = _translate(state["ocr_text"], state["language_code"])

    return updates


def _translate(text: str, language_code: str) -> str:
    """gemini-2.5-flash를 사용해 text를 한국어로 번역."""
    prompt = TRANSLATION_PROMPT.format(language=language_code, text=text)
    return llm.invoke(prompt).content
```
