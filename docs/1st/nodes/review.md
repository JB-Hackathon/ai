# 심의 노드

## 역할

법령과 체크리스트를 기반으로 심의 결과서 초안(`review_result`)을 작성한다.
gemini-2.5-flash가 텍스트와 이미지를 통합 처리하므로 단일 노드로 동작한다.

## 심의 (`review_node`)

- 모델: `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`
- 시스템 프롬프트: `"당신은 금융 광고 심의 전문가입니다. 체크리스트와 법령을 기반으로 심의 결과서를 작성해주세요."`

## 프롬프트 구성

사용자 메시지(`user_content`)는 다음 순서로 조합된다:

1. **체크리스트** — `"- {item}"` 형식으로 나열
2. **법령** — `law_list` 항목을 줄바꿈으로 나열
3. **콘텐츠** — `content_text` + `ocr_text`
4. **조건부 참고항목** (`conditional_checklist` 존재 시) — "조건부 참고항목" 섹션으로 추가 포함 (직접 적용 기준은 아니며 맥락 참고용)
5. **재심의 피드백** (`eval_feedback` 존재 시) — 이전 평가자의 개선 지시 포함
6. **이미지** (`needs_visual_review == True`이고 파일이 존재할 때) — jpg/png 파일을 base64 인코딩하여 `image_url` 메시지로 추가

## 이미지 포함 조건

| 조건 | 동작 |
|------|------|
| `needs_visual_review == True` | content_file_path의 jpg/png를 base64로 인코딩 → `image_url` 메시지 추가 |
| `needs_visual_review == False` | 텍스트만으로 처리 |

이미지 메시지 형식:
```python
{
    "type": "image_url",
    "image_url": {"url": f"data:{mime_type};base64,{encoded}"}
}
```
- MIME 타입: `.jpg` → `image/jpeg`, `.png` → `image/png`
- 텍스트 본문은 `{"type": "text", "text": prompt_text}` 형식으로 user_content 배열에 함께 전달

## 재심의 로직

- 재심의 시 이전 `eval_feedback`을 메시지에 포함하여 개선 유도
- `loop_count`가 3 미만이고 `eval_score`가 80점 미만인 경우에만 재심의

## 구현 위치

`src/nodes/review.py`
