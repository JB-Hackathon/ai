# FastAPI 엔드포인트 명세

## POST /review/{content_version_id}

심의 요청. `content_version_id`로 `review_content_versions` 테이블에서 심의 대상 데이터를 조회한 후 그래프를 실행한다.

### Request

| 이름 | 종류 | 설명 |
|------|------|------|
| `content_version_id` | path param (int) | 심의 대상 콘텐츠 버전 ID |

`review_content_versions` 테이블에서 다음 필드를 조회하여 초기 State를 구성한다:

| DB 컬럼 | State 필드 | 설명 |
|---------|-----------|------|
| `business_sector` | `business_sector` | 은행 / 여신금융 / 금융투자 / 저축은행 / 기타 |
| `channel_type` | `channel_type` | 홈페이지 / SNS / 문자, 카카오톡 / 기타 |
| `content_category` | `content_category` | 금융상품 광고 / 업무광고 / 정보제공 / 기타 |
| `product_category` | `product_category` | 상품군 (상품 광고인 경우, 없으면 None) |
| `language_code` | `language_code` | 한국어 / 영어 / 필리핀어 / 캄보디아어 / 중국어 / 베트남어 |
| `content_file_path` | `content_file_path` | 파일 경로 목록 |
| `content_text` | `content_text` | 심의 대상 텍스트 |

`thread_id`는 `str(content_version_id)`로 설정된다. 자세한 내용은 [memory.md](./memory.md) 참조.

### Response

```json
{
  "eval_score": 0.0,
  "review_result": "string",
  "checklist": ["string"],
  "law_list": ["string"],
  "eval_feedback": "string",
  "review_status": "approved"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `eval_score` | `float` | 평가 점수 (0~100) |
| `review_result` | `str` | 심의 결과서 전문 |
| `checklist` | `list[str]` | 적용된 심의 체크리스트 항목 |
| `law_list` | `list[str]` | RAG로 선별된 법령 조항 |
| `eval_feedback` | `str` | 최종 평가 피드백 |
| `review_status` | `str` | `"approved"` (score ≥ 80) 또는 `"rejected"` |

---

## GET /review/{thread_id}

> ⚠️ 미구현 (PostgreSQL 연동 이후 예정)

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

> ⚠️ 미구현 (PostgreSQL 연동 이후 예정)

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

> ⚠️ 미구현 (PostgreSQL 연동 이후 예정)

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
