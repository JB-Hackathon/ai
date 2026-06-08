# RAG 노드

## 역할

`content_text`와 `ocr_text`를 바탕으로 LLM이 검색 쿼리를 생성하고, PostgreSQL + pgvector에서 관련 법령 조항을 하이브리드 검색하여 `law_list`를 채운다.

## 처리 흐름

```
content_text + ocr_text + 메타데이터
        ↓
1. 검색 쿼리 생성 (LLM, 3~5개)
        ↓
2. 쿼리 임베딩 (gemini-embedding-2, 1024차원)
        ↓
3. 하이브리드 검색 (벡터 + BM25 + RRF)
        ↓
4. 중복 제거 → top 20 병합
        ↓
law_list 반환
```

## 검색 쿼리 생성

- 모델: `gemini-2.5-flash`
- 구조화 출력: `list[_SearchQuery]`

```python
class _SearchQuery(BaseModel):
    query: str    # 검색 쿼리 문자열
    intent: str   # 이 쿼리로 찾으려는 참조 문서 설명 (1문장)
```

- 입력: 업종, 콘텐츠 메타데이터, 콘텐츠 텍스트, 채널/매체 유형
- 폴백: LLM 호출 실패 시 `content_text + ocr_text` 전체를 단일 쿼리로 사용

## 임베딩

- 모델: `gemini-embedding-2`
- 차원: 1024
- task_type: `RETRIEVAL_QUERY`

## 하이브리드 검색

쿼리별로 벡터 유사도 검색과 BM25 전문 검색을 수행하고 RRF(Reciprocal Rank Fusion)로 병합한다.

| 파라미터 | 값 |
|---------|-----|
| 벡터 후보 수 (`_VECTOR_LIMIT`) | 30 |
| BM25 후보 수 (`_TEXT_LIMIT`) | 30 |
| RRF k 파라미터 | 60 |
| 쿼리당 top-k (`_TOP_K`) | 10 |
| 최종 병합 결과 (`_FINAL_TOP_K`) | 20 |

전체 쿼리 결과를 `_merge_chunks()`로 합산하여 중복을 제거한 뒤 상위 20개를 반환한다.

## 반환 형식

`law_list` 각 항목 형식:

```
[{법령명}] ({발령기관})
{청크 텍스트}
```

## 시각 요건 처리

`needs_visual_review`는 `ocr_node`에서 이미지 파일 또는 스캔 PDF 감지 시 `True`로 설정된다. `rag_node`는 이 값을 state에서 그대로 전달한다.

## 구현 위치

`src/nodes/rag.py`
