from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.nodes.checklist import checklist_node
from src.nodes.evaluator import evaluator_node
from src.nodes.ocr import ocr_node
from src.nodes.rag import rag_node
from src.nodes.review import review_node
from src.state import ReviewState


def should_continue(state: ReviewState) -> str:
    if state.get("eval_score", 0) >= 80 or state.get("loop_count", 0) >= 3:
        return "end"
    return "review"


def build_graph():
    builder = StateGraph(ReviewState)

    builder.add_node("ocr_node", ocr_node)
    builder.add_node("rag_node", rag_node)
    builder.add_node("checklist_node", checklist_node)
    builder.add_node("review_node", review_node)
    builder.add_node("evaluator_node", evaluator_node)

    builder.add_edge(START, "ocr_node")
    builder.add_edge("ocr_node", "rag_node")
    builder.add_edge("rag_node", "checklist_node")
    builder.add_edge("checklist_node", "review_node")
    builder.add_edge("review_node", "evaluator_node")
    builder.add_conditional_edges(
        "evaluator_node",
        should_continue,
        {"end": END, "review": "review_node"},
    )

    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
