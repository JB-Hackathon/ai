# LangGraph 체크포인트 PostgreSQL 저장 명세

AI 에이전트(LangGraph)는 심의 워크플로우 실행 중 각 노드 완료 시점마다 전체 상태를 PostgreSQL에 스냅샷으로 저장합니다.  
이 문서는 데이터 파트 및 백엔드 파트 담당자를 위해 저장 구조와 내용을 정리합니다.

---

## 1. 자동 생성 테이블

`AsyncPostgresSaver.setup()`이 앱 최초 기동 시 아래 4개 테이블을 자동 생성합니다.  
별도 스키마 설계나 마이그레이션 작업이 필요 없습니다.

| 테이블 | 역할 |
|---|---|
| `checkpoints` | 노드 완료 시점별 스냅샷 메타데이터 |
| `checkpoint_blobs` | 각 상태 필드 값 (msgpack 직렬화) |
| `checkpoint_writes` | 노드별 중간 쓰기 기록 |
| `checkpoint_migrations` | 내부 마이그레이션 버전 관리 |

> **주의:** 이 테이블들은 LangGraph가 직접 관리합니다. 외래키 제약이나 스키마 변경을 가하면 향후 버전 업그레이드 시 마이그레이션이 깨질 수 있습니다.

---

## 2. 기존 테이블과의 연결

`review_content_versions.content_version_id`를 LangGraph `thread_id`로 사용합니다.

```
review_content_versions.content_version_id (BIGINT)
        ↓  str(content_version_id)
checkpoints.thread_id (TEXT)
```

FK 제약 없이 애플리케이션 레이어에서 `thread_id = str(content_version_id)`로 조회합니다.

---

## 3. 테이블 상세

### 3.1 checkpoints

| 컬럼 | 설명 |
|---|---|
| `thread_id` | 심의 세션 ID (`content_version_id`의 문자열 변환값) |
| `checkpoint_ns` | 네임스페이스 (기본값 `""`) |
| `checkpoint_id` | 스냅샷 고유 ID (타임스탬프 기반 UUID) |
| `parent_checkpoint_id` | 직전 스냅샷 ID |
| `type` | 직렬화 타입 |
| `checkpoint` | 스냅샷 바이너리 |
| `metadata` | 실행 메타 (`step`, `source`, `parents`) |

### 3.2 checkpoint_blobs

상태 필드 값이 채널(= 필드명)별로 저장됩니다. 값은 **msgpack** 직렬화 바이너리입니다.

| 컬럼 | 설명 |
|---|---|
| `thread_id` | 심의 세션 ID |
| `checkpoint_ns` | 네임스페이스 |
| `channel` | 상태 필드명 (아래 목록 참고) |
| `version` | 해당 필드의 버전 번호 |
| `type` | 직렬화 타입 (`msgpack`) |
| `blob` | 직렬화된 필드 값 |

### 3.3 checkpoint_writes

| 컬럼 | 설명 |
|---|---|
| `thread_id` | 심의 세션 ID |
| `checkpoint_id` | 해당 스냅샷 ID |
| `task_id` | 노드 태스크 ID |
| `idx` | 쓰기 순서 인덱스 |
| `channel` | 상태 필드명 |
| `type` | 직렬화 타입 |
| `blob` | 직렬화된 필드 값 |
| `task_path` | 노드 경로 |

---

## 4. 저장되는 ReviewState 필드

심의 1회 실행 시 아래 모든 필드가 체크포인트마다 저장됩니다.

| 필드 | 타입 | 저장 예시 |
|---|---|---|
| `content_text` | str | 광고 원문 텍스트 (2040자) |
| `content_file_path` | list[str] | 업로드 파일 경로 목록 |
| `channel_type` | str | `"sns"` |
| `content_category` | str | `"product_ad"` |
| `product_category` | str\|None | `"deposit"` |
| `business_sector` | str | `"bank"` |
| `language_code` | str | `"ko"` |
| `ocr_text` | str | OCR 추출 텍스트 (549자) |
| `law_list` | list[str] | 관련 법령 조항 10개 |
| `checklist` | list[str] | 심의 체크리스트 16개 항목 |
| `needs_visual_review` | bool | `True` (이미지 포함 시) |
| `review_result` | str | 심의 결과서 전문 (45,033자) |
| `eval_score` | float | `95.0` |
| `eval_feedback` | str | 평가 피드백 (345자) |
| `loop_count` | int | `2` (재심의 횟수) |
| `review_passed` | bool | `True` |
| `messages` | list | 대화 로그 (현재 미사용, 빈 배열) |

---

## 5. 실행 1회당 저장 레코드 수

노드가 완료될 때마다 스냅샷 1개가 생성됩니다.

```
step -1 : input          (초기 입력)
step  0 : ocr_node
step  1 : rag_node
step  2 : checklist_node
step  3 : review_node
step  4 : evaluator_node
step  5 : review_node    ← 재심의 (eval_score < 80)
step  6 : evaluator_node ← 재평가
step  7 : 종료
```

- `loop_count = 1` (재심의 없음): **checkpoints 6개**, checkpoint_writes ~24개
- `loop_count = 2` (재심의 1회): **checkpoints 9개**, checkpoint_writes ~39개
- `loop_count = 3` (최대): **checkpoints 12개**, checkpoint_writes ~54개

---

## 6. 데이터 조회 방법

### SQL (메타데이터 확인용)

```sql
-- 특정 content_version_id의 체크포인트 목록
SELECT thread_id, checkpoint_id, metadata
FROM checkpoints
WHERE thread_id = '1'   -- content_version_id
ORDER BY checkpoint_id;

-- 저장된 필드 목록 및 크기 확인
SELECT channel, type, length(blob) AS blob_size
FROM checkpoint_blobs
WHERE thread_id = '1'
ORDER BY channel;
```

> **주의:** `checkpoint_blobs.blob`은 msgpack 바이너리라 SQL로 직접 값을 읽을 수 없습니다.

### LangGraph API (Python, 실제 값 복원)

```python
config = {"configurable": {"thread_id": str(content_version_id)}}

# 최종 상태 조회
state = await graph.aget_state(config)
print(state.values["review_result"])
print(state.values["eval_score"])

# 노드별 실행 히스토리
async for snapshot in graph.aget_state_history(config):
    print(snapshot.metadata["step"], snapshot.next)
```
