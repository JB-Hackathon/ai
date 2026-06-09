import argparse
import asyncio
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage  # noqa: E402
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402

from src.chatbot.graph import build_graph as build_chatbot_graph  # noqa: E402
from src.graph import build_graph  # noqa: E402

_PHASE1_FIELDS = [
    "review_result",
    "law_list",
    "checklist",
    "conditional_checklist",
    "content_text",
    "ocr_text",
    "channel_type",
    "content_category",
    "product_category",
    "business_sector",
    "eval_score",
    "eval_feedback",
    "review_passed",
    "needs_visual_review",
]

_NODE_NAMES = {"chatbot_node", "tools"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="챗봇 대화형 테스트")
    parser.add_argument(
        "--phase1-thread-id",
        required=True,
        help="run_graph.py 실행 시 출력된 thread_id",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL", "postgresql://jbuser:jbpass@localhost:5432/jbdb")

    async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
        await checkpointer.setup()
        _graph = build_graph(checkpointer)
        _chatbot_graph = build_chatbot_graph(checkpointer)

        snapshot = await _graph.aget_state(
            {"configurable": {"thread_id": args.phase1_thread_id}}
        )
        if not snapshot.values:
            print(f"오류: thread_id '{args.phase1_thread_id}'에 해당하는 Phase 1 결과가 없습니다.")
            return

        phase1_state = {field: snapshot.values[field] for field in _PHASE1_FIELDS}
        chatbot_thread_id = str(uuid.uuid4())

        print(f"Phase 1 thread_id : {args.phase1_thread_id}")
        print(f"챗봇 thread_id    : {chatbot_thread_id}")
        print("대화를 시작합니다. 종료하려면 빈 줄 또는 quit/exit 입력.\n")

        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n종료합니다.")
                break

            if not user_input or user_input in ("quit", "exit"):
                print("종료합니다.")
                break

            turn_state = {**phase1_state, "messages": [HumanMessage(content=user_input)]}
            config = {"configurable": {"thread_id": chatbot_thread_id}}

            async for event in _chatbot_graph.astream_events(
                turn_state, config=config, version="v2"
            ):
                kind = event["event"]
                name = event.get("name", "")
                if name not in _NODE_NAMES:
                    continue
                if kind == "on_chain_start":
                    print(f"  ▶ [{name}] 시작")
                elif kind == "on_chain_end":
                    print(f"  ✓ [{name}] 완료")

            db_snapshot = await _chatbot_graph.aget_state(config)
            msgs = db_snapshot.values["messages"]
            print(f"\n[AI] {msgs[-1].content}")
            print(f"  (DB 저장 메시지 수: {len(msgs)})\n")


if __name__ == "__main__":
    asyncio.run(main())
