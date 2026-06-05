# 체크리스트 생성 노드

## 역할

입력 내용(`input_text`, `ocr_text`)과 RAG로 찾은 관련 법령(`law_list`)을 기반으로, LLM이 심의 생성 및 평가에 사용할 가이드라인 체크리스트를 생성한다.

## 입력

- `input_text`, `ocr_text`
- `law_list`

## 출력

- `checklist: list[str]`

## 구현 상세

- **모델**: `gemini-2.5-flash`
- **출력 파싱**: `with_structured_output(ChecklistOutput)` 사용

```python
class ChecklistOutput(BaseModel):
    items: list[str]

# → state["checklist"] = result.items
```

- **프롬프트 패턴**: 관련 법령(`law_list`)과 심의 대상 텍스트(`input_text`, `ocr_text`)를 입력으로 받아, 심의 및 평가 기준으로 사용할 체크리스트 항목을 생성한다.

## 구현 위치

`src/nodes/checklist.py`
