# FastAPI 엔드포인트 명세

## POST /thread/{thread_id}

챗봇 메시지 전송. `thread_id`(UUID)로 `chat_threads` 테이블에서 `content_version_id`를 조회하고, Phase 1 체크포인터에서 초기 상태를 로드하여 챗봇 그래프를 실행한다.

### Request

| 이름 | 종류 | 타입 | 설명 |
|------|------|------|------|
| `thread_id` | path param | UUID (str) | 챗봇 스레드 ID (`chat_threads.thread_id`) |
| `message` | body | str | 사용자 메시지 |

```json
{
  "message": "○○ 법령이 누락된 것 같습니다."
}
```

### 처리 흐름

1. `chat_threads` 테이블에서 `thread_id` → `content_version_id` 조회
2. Phase 1 체크포인터에서 `str(content_version_id)` thread 상태 로드 → `ChatState` 초기값 14개 필드 추출
3. `ChatState` 초기값 + `HumanMessage(content=message)` 조합
4. 챗봇 그래프 `ainvoke` 실행
5. `messages[-1].content` 반환

### Response

```json
{
  "reply": "string"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `reply` | `str` | 챗봇의 최종 응답 메시지 (일반 응답 또는 수정된 심의 결과 요약) |

### 오류

| 상태 코드 | 원인 |
|----------|------|
| 404 | `thread_id`에 해당하는 `chat_threads` 레코드 없음 |
| 404 | `content_version_id`에 해당하는 Phase 1 체크포인트 없음 |
| 422 | `message` 필드 누락 |
