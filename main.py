import os
from contextlib import asynccontextmanager

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv()

from src.graph import build_graph  # noqa: E402

_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
        await checkpointer.setup()
        _graph = build_graph(checkpointer)
        yield


app = FastAPI(
    title="JB-Hackathon AI Service",
    description="AI 에이전트 서빙을 위한 FastAPI 서버",
    version="1.0.0",
    lifespan=lifespan,
)


class ReviewResponse(BaseModel):
    eval_score: float
    review_result: str
    checklist: list[str]
    conditional_checklist: list[str]
    law_list: list[str]
    eval_feedback: str
    review_status: str  # "approved" | "rejected"


def _fetch_content_version(content_version_id: int) -> dict | None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    with psycopg.connect(database_url) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT business_sector, channel_type, content_category,
                   product_category, language_code, content_file_path, content_text
            FROM review_content_versions
            WHERE content_version_id = %s AND deleted_at IS NULL
            """,
            (content_version_id,),
        )
        return cur.fetchone()


@app.get("/")
def ping_get():
    return {"status": "success", "message": "pong (GET)"}


@app.post("/ping")
async def ping_post():
    return {"status": "success", "message": "pong (POST)"}


@app.post("/review/{content_version_id}", response_model=ReviewResponse)
async def start_review(content_version_id: int):
    row = _fetch_content_version(content_version_id)
    if row is None:
        raise HTTPException(status_code=404, detail="심의 콘텐츠 버전을 찾을 수 없습니다.")

    files = [f.strip() for f in (row["content_file_path"] or "").split("\n") if f.strip()]

    initial_state = {
        "content_text": row["content_text"] or "",
        "content_file_path": files,
        "channel_type": row["channel_type"],
        "content_category": row["content_category"],
        "product_category": row["product_category"],
        "business_sector": row["business_sector"],
        "language_code": row["language_code"],
        "ocr_text": "",
        "original_content_text": "",
        "original_ocr_text": "",
        "law_list": [],
        "checklist": [],
        "conditional_checklist": [],
        "needs_visual_review": False,
        "review_result": "",
        "eval_score": 0.0,
        "eval_feedback": "",
        "loop_count": 0,
        "review_passed": False,
        "messages": [],
    }

    thread_id = str(content_version_id)
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await _graph.ainvoke(initial_state, config=config)

    review_status = "approved" if final_state["review_passed"] else "rejected"
    return ReviewResponse(
        eval_score=final_state["eval_score"],
        review_result=final_state["review_result"],
        checklist=final_state["checklist"],
        conditional_checklist=final_state.get("conditional_checklist", []),
        law_list=final_state["law_list"],
        eval_feedback=final_state["eval_feedback"],
        review_status=review_status,
    )
