import os
import shutil
import tempfile
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.graph import graph

app = FastAPI()


class ReviewResponse(BaseModel):
    thread_id: str
    review_result: str
    eval_score: float
    eval_feedback: str
    law_list: list[str]
    checklist: list[str]
    loop_count: int
    review_passed: bool


@app.post("/review", response_model=ReviewResponse)
async def review(
    input_text: str = Form(""),
    channel: str = Form(...),
    content_type: str = Form(...),
    product_category: Optional[str] = Form(None),
    industry: str = Form(...),
    language: str = Form(...),
    input_files: list[UploadFile] = File(default=[]),
):
    if not input_text.strip() and not input_files:
        raise HTTPException(status_code=422, detail="input_text 또는 input_files 중 하나는 필수입니다.")

    thread_id = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp()
    saved_paths = []

    try:
        for file in input_files:
            dest = os.path.join(tmp_dir, file.filename)
            with open(dest, "wb") as f:
                f.write(await file.read())
            saved_paths.append(dest)

        initial_state = {
            "input_text": input_text,
            "input_files": saved_paths,
            "channel": channel,
            "content_type": content_type,
            "product_category": product_category,
            "industry": industry,
            "language": language,
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

        config = {"configurable": {"thread_id": thread_id}}
        final_state = await graph.ainvoke(initial_state, config=config)

        return ReviewResponse(
            thread_id=thread_id,
            review_result=final_state["review_result"],
            eval_score=final_state["eval_score"],
            eval_feedback=final_state["eval_feedback"],
            law_list=final_state["law_list"],
            checklist=final_state["checklist"],
            loop_count=final_state["loop_count"],
            review_passed=final_state["review_passed"],
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
