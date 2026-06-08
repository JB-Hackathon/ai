import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402

from src.graph import build_graph  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LangGraph 심의 테스트 실행")
    parser.add_argument("--case", required=True, help="케이스 디렉터리 경로 (review_content_version.json 포함)")
    return parser.parse_args()


def load_case(case_dir: str) -> dict:
    p = Path(case_dir)
    data = json.loads((p / "review_content_version.json").read_text(encoding="utf-8"))
    files = [
        str(p / f.strip())
        for f in data.get("content_file_path", "").split("\n")
        if f.strip()
    ]
    return {
        "content_text": data.get("content_text", ""),
        "content_file_path": files,
        "channel_type": data.get("channel_type", ""),
        "content_category": data.get("content_category", ""),
        "product_category": data.get("product_category"),
        "business_sector": data.get("business_sector", ""),
        "language_code": data.get("language_code", ""),
    }


async def main() -> None:
    args = parse_args()
    thread_id = str(uuid.uuid4())
    database_url = os.getenv("DATABASE_URL", "postgresql://jbuser:jbpass@localhost:5432/jbdb")

    async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
        await checkpointer.setup()
        graph = build_graph(checkpointer)

        await _run(args, thread_id, graph)


_NODE_NAMES = {
    "ocr_node",
    "translation_node",
    "rag_node",
    "checklist_node",
    "review_node",
    "evaluator_node",
}


async def _run(args, thread_id, graph) -> None:
    initial_state = {
        **load_case(args.case),
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

    print(f"thread_id: {thread_id}")
    print("그래프 실행 중...")

    state_updates: dict = {}
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event["event"]
        name = event.get("name", "")
        if name not in _NODE_NAMES:
            continue
        if kind == "on_chain_start":
            print(f"  ▶ [{name}] 시작")
        elif kind == "on_chain_end":
            print(f"  ✓ [{name}] 완료")
            output = event["data"].get("output")
            if isinstance(output, dict):
                state_updates.update(output)

    final_state = {**initial_state, **state_updates}

    print("완료!")
    print("=" * 60)
    print("요약")
    print("=" * 60)
    print(f"thread_id    : {thread_id}")
    print(f"eval_score   : {final_state['eval_score']}")
    print(f"loop_count   : {final_state['loop_count']}")
    print(f"review_passed: {final_state['review_passed']}")

    print()
    print("=" * 60)
    print("관련 법령")
    print("=" * 60)
    for i, law in enumerate(final_state["law_list"], 1):
        print(f"{i}. {law}")

    print()
    print("=" * 60)
    print("체크리스트")
    print("=" * 60)
    for i, item in enumerate(final_state["checklist"], 1):
        print(f"{i}. {item}")

    print()
    print("=" * 60)
    print("평가 피드백")
    print("=" * 60)
    print(final_state["eval_feedback"])

    print()
    print("=" * 60)
    print("심의 결과서")
    print("=" * 60)
    print(final_state["review_result"])

    output = {
        "thread_id": thread_id,
        "eval_score": final_state["eval_score"],
        "loop_count": final_state["loop_count"],
        "review_passed": final_state["review_passed"],
        "law_list": final_state["law_list"],
        "checklist": final_state["checklist"],
        "eval_feedback": final_state["eval_feedback"],
        "review_result": final_state["review_result"],
    }
    case_path = Path(args.case)
    json_path = case_path / "review_result.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    law_text = "\n".join(f"{i}. {law}" for i, law in enumerate(output["law_list"], 1))
    checklist_text = "\n".join(f"{i}. {item}" for i, item in enumerate(output["checklist"], 1))
    md_content = f"""# 심의 결과

## 요약
- thread_id: {thread_id}
- eval_score: {output['eval_score']}
- loop_count: {output['loop_count']}
- review_passed: {output['review_passed']}

## 관련 법령
{law_text}

## 체크리스트
{checklist_text}

## 평가 피드백
{output['eval_feedback']}

## 심의 결과서
{output['review_result']}
"""
    md_path = case_path / "review_result.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"\n결과 저장: {json_path}, {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
