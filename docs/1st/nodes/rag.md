# RAG 노드

## 역할

`input_text`와 `ocr_text`를 쿼리로 PostgreSQL + pgvector에서 관련 법령 조항을 검색하여 `law_list`를 채운다.

## 벡터 스토어 구성

- 청킹: `RecursiveCharacterTextSplitter`로 `data/` 디렉터리의 법령 텍스트 분할
- 임베딩: `GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")` (768차원)
- 저장: PostgreSQL + pgvector (`DATABASE_URL` 환경 변수)
- `data/` 없을 경우: 빈 DB로 시작, 법령 추가 시 자동 인덱싱

## 검색 로직

- 쿼리: `input_text + ocr_text` 결합
- 반환: top-k=10 유사 청크

## 시각 요건 감지

`ocr_node`가 `needs_visual_review` 필드를 먼저 채운다 (이미지 파일 또는 스캔 PDF 감지 시 `True`). `rag_node`는 이 값이 이미 `True`면 LLM 판단을 건너뛴다.

`needs_visual_review`가 아직 `False`인 경우에만, top-k 청크 전문을 LLM에 전달하여 시각적 표현 요건 포함 여부를 추가 판단한다.

- 모델: `gemini-2.5-flash`
- 응답 방식: `with_structured_output(VisualReviewFlag)` — 프롬프트 내 JSON 지시 없이 Pydantic 모델로 안정적 파싱

```python
class VisualReviewFlag(BaseModel):
    needs_visual_review: bool
```

- 프롬프트: "아래 광고 콘텐츠와 관련 법령 조항을 검토하여, 이 콘텐츠에 대해 시각적 표현 방식(글자 크기, 색상 대비, 강조 표시 등)의 준수 여부를 확인해야 합니까?"
- 입력: `input_text + ocr_text` (심의 대상 콘텐츠) + `law_list` 전문
- 출력: `needs_visual_review: bool`

> **변경 이유**: 스캔 PDF는 `.pdf` 확장자지만 Gemini Vision으로 처리되므로 파일 확장자만으로 판단하면 시각 요건이 누락된다. `ocr_node`에서 Vision 사용 여부를 감지하여 선행 설정하는 방식으로 대체한다.

## 구현 위치

- `src/vector_store/store.py` — PostgreSQL + pgvector 초기화 및 인덱싱
- `src/nodes/rag.py` — 검색 노드
