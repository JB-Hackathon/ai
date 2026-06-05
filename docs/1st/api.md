# FastAPI 엔드포인트 명세

## POST /review

심의 요청. multipart/form-data로 텍스트 필드와 파일을 함께 전송한다.

### Request

> **검증**: `input_text`가 비어 있고 `input_files[]`도 없으면 HTTP 422를 반환한다. 둘 중 하나는 반드시 있어야 한다.

| 이름 | 종류 | 필수 | 설명 |
|------|------|------|------|
| `input_text` | field | 조건부 | 심의 대상 텍스트 (`input_files[]` 없으면 필수) |
| `channel` | field | Y | 홈페이지 / SNS / 문자, 카카오톡 / 기타 |
| `content_type` | field | Y | 금융상품 광고 / 업무광고 / 정보제공 / 기타 |
| `product_category` | field | N | 상품군 (상품 광고인 경우) |
| `industry` | field | Y | 은행 / 여신금융 / 금융투자 / 저축은행 / 기타 |
| `language` | field | Y | 한국어 / 영어 / 필리핀어 / 캄보디아어 / 중국어 / 베트남어 |
| `input_files[]` | file | N | 이미지 / PDF / DOCX / HWP |

### Response

```json
{
  "thread_id": "string",
  "review_result": "string",
  "eval_score": 0.0,
  "eval_feedback": "string",
  "law_list": ["string"],
  "checklist": ["string"],
  "loop_count": 0,
  "review_passed": true
}
```

`thread_id`는 이 심의 세션의 고유 식별자다. 챗봇(준법 자문가 검토)에서 심의 결과를 로드하거나 수정할 때 사용한다. 자세한 내용은 [memory.md](./memory.md) 참조.

---

## GET /review/{thread_id}

심의 결과 조회. 준법 자문가 챗봇이 완료된 심의 결과를 로드할 때 사용한다 (`graph.aget_state` 기반).

### Response

```json
{
  "thread_id": "string",
  "review_result": "string",
  "eval_score": 0.0,
  "eval_feedback": "string",
  "law_list": ["string"],
  "checklist": ["string"],
  "loop_count": 0,
  "review_passed": true
}
```

---

## PATCH /review/{thread_id}

심의 결과 수정. 준법 자문가가 `review_result` 또는 `checklist`를 직접 수정할 때 사용한다 (`graph.aupdate_state` 기반).

### Request

```json
{
  "review_result": "string (optional)",
  "checklist": ["string (optional)"]
}
```

### Response

```json
{
  "status": "ok"
}
```

---

## POST /ingest

법령 데이터 인덱싱 트리거. `data/` 디렉터리 경로를 수신하여 PostgreSQL+pgvector에 인덱싱한다.

### Request

```json
{
  "data_dir": "string"
}
```

### Response

```json
{
  "status": "ok",
  "indexed_count": 0
}
```
