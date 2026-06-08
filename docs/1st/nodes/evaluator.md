# 평가자 노드

## 역할

심의 결과서(`review_result`)를 체크리스트 기준으로 검증하고 점수와 피드백을 반환한다.
점수 미달 시 재심의 루프로 돌려보내고, 3회 초과 시 강제 종료한다.

## 평가 기준

- 모델: `gemini-2.5-flash`
- 입력: `review_result` + `checklist` + `law_list` + `content_text` + `ocr_text`
- 출력: `with_structured_output(EvalOutput)` — 다른 노드와 동일한 패턴으로 파싱 안정성 확보

```python
class EvalOutput(BaseModel):
    score: float
    feedback: str
```

## loop_count 관리

- **초기값**: `main.py`의 `initial_state`에서 `loop_count: 0`으로 설정
- **증가**: `evaluator_node`에서 매 실행마다 `loop_count + 1` 반환
  ```python
  return {
      "eval_score": result.score,
      "eval_feedback": result.feedback,
      "loop_count": state["loop_count"] + 1,
      ...
  }
  ```

## 루프 종료 조건

| 조건 | 동작 |
|------|------|
| `eval_score >= 80` | `review_passed = True` → END |
| `loop_count >= 3` | `review_passed = False` → END (강제 종료, 현재 결과 그대로 반환) |
| `eval_score < 80` and `loop_count < 3` | → `review_*_node` (재심의) |

## 구현 위치

`src/nodes/evaluator.py`
