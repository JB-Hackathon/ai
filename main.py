import os
from contextlib import asynccontextmanager

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv()

from src.chatbot.graph import build_graph as build_chatbot_graph  # noqa: E402
from src.graph import build_graph  # noqa: E402

_graph = None
_chatbot_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph, _chatbot_graph
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
        await checkpointer.setup()
        _graph = build_graph(checkpointer)
        _chatbot_graph = build_chatbot_graph(checkpointer)
        yield


app = FastAPI(
    title="JB-Hackathon AI Service",
    description="AI 에이전트 서빙을 위한 FastAPI 서버",
    version="1.0.0",
    lifespan=lifespan,
)


class ChatbotRequest(BaseModel):
    message: str


class ChatbotResponse(BaseModel):
    reply: str


class ReviewResponse(BaseModel):
    eval_score: float
    review_result: str
    checklist: list[str]
    law_list: list[str]
    eval_feedback: str
    review_status: str  # "approved" | "rejected"


def _fetch_chat_thread(thread_id: str) -> dict | None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    with psycopg.connect(database_url) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT content_version_id FROM chat_threads WHERE thread_id = %s",
            (thread_id,),
        )
        return cur.fetchone()


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
        "law_list": [],
        "checklist": [],
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
        law_list=final_state["law_list"],
        eval_feedback=final_state["eval_feedback"],
        review_status=review_status,
    )


@app.post("/thread/{thread_id}", response_model=ChatbotResponse)
async def send_chatbot_message(thread_id: str, body: ChatbotRequest):
    row = _fetch_chat_thread(thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail="챗봇 스레드를 찾을 수 없습니다.")

    content_version_id = row["content_version_id"]
    snapshot = await _graph.aget_state({"configurable": {"thread_id": str(content_version_id)}})
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Phase 1 심의 결과를 찾을 수 없습니다.")

    phase1 = snapshot.values
    _phase1_fields = [
        "review_result", "law_list", "checklist", "conditional_checklist",
        "content_text", "ocr_text", "channel_type", "content_category",
        "product_category", "business_sector", "eval_score", "eval_feedback",
        "review_passed", "needs_visual_review",
    ]
    initial_state = {field: phase1[field] for field in _phase1_fields}
    initial_state["messages"] = [HumanMessage(content=body.message)]

    config = {"configurable": {"thread_id": thread_id}}
    final_state = await _chatbot_graph.ainvoke(initial_state, config=config)

    return ChatbotResponse(reply=final_state["messages"][-1].content)
