# 심의 노드

## 역할

법령과 체크리스트를 기반으로 심의 결과서 초안(`review_result`)을 작성한다.
gemini-2.5-flash가 텍스트와 이미지를 통합 처리하므로 단일 노드로 동작한다.

## 심의 (`review_node`)

- 모델: `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`
- 입력: system 프롬프트 + 체크리스트 + 법령 + `input_text` + `ocr_text`
- 이미지 포함 조건:

| 조건 | 동작 |
|------|------|
| `needs_visual_review == True` | 이미지 VLM 요청에 포함 (이미지 존재가 보장됨) |
| `needs_visual_review == False` | 텍스트만으로 처리 (이미지 불포함) |

## 재심의 로직

- 재심의 시 이전 `eval_feedback`을 메시지에 포함하여 개선 유도
- `loop_count`가 3 미만이고 `eval_score`가 80점 미만인 경우에만 재심의

## 구현 위치

`src/nodes/review.py`
