# 체크리스트 생성 노드

## 역할

RAG로 검색된 참고문서(`law_list`)에서 준법심의 기준 후보를 추출하고, 각 기준이 콘텐츠 원문에 실제로 적용되는지 판단하여 체크리스트를 생성한다. 적용되지 않는 기준은 "조건부 참고항목"으로 분리한다.

## 입력

- `content_text`, `ocr_text` — 콘텐츠 원문
- `channel_type`, `content_category`, `product_category`, `business_sector`, `language_code` — 사용자 입력 정보
- `law_list` — RAG 검색 결과 참고문서 조각

## 출력

- `checklist: list[str]` — 콘텐츠에 직접 적용되는 기준 (HIGH → MEDIUM → LOW 순 정렬)
- `conditional_checklist: list[str]` — 조건부 참고항목 (직접 미적용 기준)

## 구현 상세

- **모델**: `gemini-2.5-flash`
- **출력 파싱**: `with_structured_output(ChecklistOutput)` 사용

```python
class ChecklistItem(BaseModel):
    item: str                              # 체크항목
    reason: str                            # 적용 이유
    trigger_expression: str                # 콘텐츠 내 트리거 표현
    source_document: str                   # 근거 문서
    check_method: str                      # 점검 방법
    priority: Literal["HIGH", "MEDIUM", "LOW"]  # 우선순위
    uncertainty: str                       # 불확실성 (없으면 빈 문자열)

class ChecklistOutput(BaseModel):
    items: list[ChecklistItem]
    conditional_items: list[ChecklistItem] = []

# → state["checklist"] = 직렬화된 items (HIGH→MEDIUM→LOW 정렬)
# → state["conditional_checklist"] = 직렬화된 conditional_items
```

- **직렬화 형식** (`_serialize_item`):

```
[1] 체크항목 텍스트
  - 적용 이유: ...
  - 트리거 표현: ...
  - 근거 문서: ...
  - 점검 방법: ...
  - 우선순위: HIGH
  - 불확실성: ... (있을 때만)
```

- **프롬프트 패턴**:
  1. 검색된 참고문서에서 준법심의 기준 후보 추출
  2. 각 기준이 콘텐츠 원문에 적용되는지 판단 (표현·상품 유형·채널 특성 확인)
  3. 적용 기준만 `items` 생성
  4. 미적용 기준은 `conditional_items` 분리
  5. 검색 근거 없는 항목 생성 금지

## 구현 위치

`src/nodes/checklist.py`
