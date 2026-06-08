from __future__ import annotations

import os
from dataclasses import dataclass
from typing import LiteralString

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field


_DEFAULT_DATABASE_URL = "postgresql://jbuser:jbpass@localhost:5432/jbdb"
_EMBEDDING_MODEL = "gemini-embedding-2"
_EMBEDDING_DIMENSIONALITY = 1024
_LLM_MODEL = "gemini-2.5-flash"
_TOP_K = 10
_VECTOR_LIMIT = 30
_TEXT_LIMIT = 30
_RRF_K = 60
_FINAL_TOP_K = 20


class _SearchQuery(BaseModel):
    query: str = Field(description="문서 탐색 목적이 드러나는 문장형/구문형 쿼리")
    intent: str = Field(description="이 쿼리로 찾으려는 참고문서 유형 (1문장)")


class _QueryGenerationOutput(BaseModel):
    queries: list[_SearchQuery] = Field(description="생성된 탐색 쿼리 목록 (3~5개)")


@dataclass(frozen=True, slots=True)
class _LawChunk:
    title: str
    issuing_authority: str
    chunk_text: str


_SYSTEM_QUERY_GEN = """\
너는 금융 콘텐츠 준법심의용 RAG 탐색 쿼리 생성기다.

목표:
입력 콘텐츠에 실제 적용될 수 있는 준법심의 체크항목을 참고문서에서 찾아내기 위해,
관련 법령, 감독규정, 협회 기준, 가이드라인, 보도자료, 점검사례를 검색할 탐색 쿼리를 생성한다.

중요 원칙:
1. 너는 아직 어떤 체크항목이 적용되는지 모른다.
2. 따라서 체크해야 할 세부 항목을 사전에 단정해서 쿼리에 넣지 마라.
   예: 기본금리, 우대금리 조건, 예금자보호 문구, 중도상환수수료, 부대비용, 손실가능성,
   수수료 등은 콘텐츠 원문 또는 이전 검색 결과에 명시되어 있지 않으면 쿼리에 넣지 않는다.
3. 쿼리의 목적은 정답을 직접 묻는 것이 아니라,
   체크항목을 담고 있을 가능성이 높은 참고문서를 찾는 것이다.
4. 콘텐츠 원문에서 표면적으로 확인 가능한 단어만 사용한다.
5. 다음 일반 탐색어는 사용할 수 있다:
   광고, 금융상품 광고, 업무광고, 규정, 심의 기준, 가이드라인, 유의사항,
   점검결과, 적용사례, 법률, 시행령, 감독규정, 표시, 설명, 소비자 오인
6. 상품유형도 확정하지 말고, 필요한 경우 "후보"로 표현한다.
7. 쿼리는 짧은 키워드 나열이 아니라 문서 탐색 목적이 드러나는 문장형 또는 구문형으로 만든다.
8. 3~5개의 쿼리를 생성한다. 각 쿼리마다 어떤 참고문서를 찾기 위한 것인지 intent를 붙인다.

작업 순서:
1. 콘텐츠 표면 분석을 수행한다.
   - raw_product_terms: 상품명, 서비스명, 상품군으로 보이는 원문 단어
   - raw_claim_terms: 금리, 수익률, 한도, 혜택, 무료, 빠름, 안전, 추천 등 강조 표현
   - action_terms: 가입, 신청, 상담, 조회, 개설, 다운로드 등 행동 유도 표현
   - numbers: %, 원, 개월, 일 등 숫자 표현
   - channel_terms: 앱, 홈페이지, SNS, 유튜브, 배너, 문자 등 매체 표현
   - estimated_content_type: 금융상품 광고 후보 / 업무광고 후보 / 단순 안내 후보 / 이벤트 후보 등
2. 표면 분석 결과를 바탕으로 탐색 쿼리를 생성한다.
3. 쿼리에는 원문에 없는 세부 체크항목을 넣지 않는다.\
"""


def _build_query_gen_message(state: dict) -> str:
    content_parts = []
    if state.get("content_text"):
        content_parts.append(state["content_text"])
    if state.get("ocr_text"):
        content_parts.append(f"[OCR 추출]\n{state['ocr_text']}")
    content_text = "\n\n".join(content_parts) or "(없음)"

    metadata_parts = []
    if state.get("content_category"):
        metadata_parts.append(f"콘텐츠 유형: {state['content_category']}")
    if state.get("product_category"):
        metadata_parts.append(f"상품 범주: {state['product_category']}")
    if state.get("language_code"):
        metadata_parts.append(f"언어: {state['language_code']}")
    metadata = ", ".join(metadata_parts) or "(없음)"

    return (
        f"- 업권: {state.get('business_sector', '미상')}\n"
        f"- 콘텐츠 원문:\n{content_text}\n"
        f"- 채널 또는 매체: {state.get('channel_type', '미상')}\n"
        f"- 추가 메타데이터: {metadata}"
    )


def _generate_search_queries(state: dict) -> list[_SearchQuery]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    try:
        llm = ChatGoogleGenerativeAI(model=_LLM_MODEL)
        result: _QueryGenerationOutput = llm.with_structured_output(_QueryGenerationOutput).invoke(
            [
                SystemMessage(content=_SYSTEM_QUERY_GEN),
                HumanMessage(content=_build_query_gen_message(state)),
            ]
        )
        return result.queries
    except Exception:
        query_parts = [state.get("content_text", ""), state.get("ocr_text", "")]
        fallback = "\n".join(p for p in query_parts if p).strip()
        if not fallback:
            return []
        return [_SearchQuery(query=fallback, intent="콘텐츠 전체 탐색")]


def _merge_chunks(chunks_per_query: list[list[_LawChunk]]) -> list[_LawChunk]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[_LawChunk] = []
    for chunks in chunks_per_query:
        for chunk in chunks:
            key = (chunk.title, chunk.issuing_authority, chunk.chunk_text)
            if key not in seen:
                seen.add(key)
                merged.append(chunk)
    return merged[:_FINAL_TOP_K]


def rag_node(state: dict) -> dict:
    queries = _generate_search_queries(state)

    if not queries:
        return {
            "law_list": [],
            "needs_visual_review": state.get("needs_visual_review", False),
        }

    chunks_per_query: list[list[_LawChunk]] = []
    for sq in queries:
        embedding = _embed_query(sq.query)
        chunks = _search_laws(sq.query, embedding)
        chunks_per_query.append(chunks)

    merged = _merge_chunks(chunks_per_query)
    law_list = [f"[{c.title}] ({c.issuing_authority})\n{c.chunk_text}" for c in merged]

    return {
        "law_list": law_list,
        "needs_visual_review": state.get("needs_visual_review", False),
    }


def _embed_query(query: str) -> list[float]:
    from google import genai
    from google.genai import types

    client = genai.Client()
    response = client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=[query],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=_EMBEDDING_DIMENSIONALITY,
        ),
    )
    embeddings = response.embeddings
    if not embeddings or embeddings[0].values is None:
        raise RuntimeError("Google embedding response did not contain values")
    return [float(v) for v in embeddings[0].values]


def _search_laws(query: str, query_embedding: list[float]) -> list[_LawChunk]:
    database_url = os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL)
    params: dict[str, object] = {
        "query": query,
        "query_embedding": "[" + ",".join(str(v) for v in query_embedding) + "]",
        "top_k": _TOP_K,
        "vector_limit": _VECTOR_LIMIT,
        "text_limit": _TEXT_LIMIT,
        "rrf_k": _RRF_K,
        "document_type": None,
        "issuing_authority": None,
    }

    with psycopg.connect(database_url) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_hybrid_search_sql(), params)
        rows = cur.fetchall()

    return [
        _LawChunk(
            title=str(row["title"]),
            issuing_authority=str(row["issuing_authority"]),
            chunk_text=str(row["chunk_text"]),
        )
        for row in rows
    ]


def _hybrid_search_sql() -> LiteralString:
    return """
    WITH query AS (
      SELECT
        %(query_embedding)s::vector AS embedding,
        websearch_to_tsquery('simple', %(query)s) AS ts_query
    ),
    filtered_chunks AS (
      SELECT
        c.chunk_id,
        c.chunk_text,
        c.embedding,
        c.search_vector,
        d.title,
        d.issuing_authority
      FROM reference_document_chunks c
      JOIN reference_documents d ON d.document_id = c.document_id
      WHERE (%(document_type)s::text IS NULL OR d.document_type::text = %(document_type)s::text)
        AND (%(issuing_authority)s::text IS NULL OR d.issuing_authority = %(issuing_authority)s::text)
    ),
    vector_matches AS (
      SELECT
        chunk_id,
        row_number() OVER (ORDER BY embedding <=> (SELECT embedding FROM query)) AS vector_rank
      FROM filtered_chunks
      ORDER BY embedding <=> (SELECT embedding FROM query)
      LIMIT %(vector_limit)s
    ),
    text_matches AS (
      SELECT
        chunk_id,
        row_number() OVER (ORDER BY ts_rank_cd(search_vector, (SELECT ts_query FROM query)) DESC) AS text_rank
      FROM filtered_chunks
      WHERE search_vector @@ (SELECT ts_query FROM query)
      ORDER BY ts_rank_cd(search_vector, (SELECT ts_query FROM query)) DESC
      LIMIT %(text_limit)s
    ),
    combined AS (
      SELECT
        COALESCE(v.chunk_id, t.chunk_id) AS chunk_id,
        COALESCE(1.0 / (%(rrf_k)s + v.vector_rank), 0.0)
          + COALESCE(1.0 / (%(rrf_k)s + t.text_rank), 0.0) AS rrf_score,
        v.vector_rank,
        t.text_rank
      FROM vector_matches v
      FULL OUTER JOIN text_matches t ON t.chunk_id = v.chunk_id
    )
    SELECT
      f.title,
      f.issuing_authority,
      f.chunk_text
    FROM combined c
    JOIN filtered_chunks f ON f.chunk_id = c.chunk_id
    ORDER BY c.rrf_score DESC, c.vector_rank NULLS LAST, c.text_rank NULLS LAST
    LIMIT %(top_k)s
    """
