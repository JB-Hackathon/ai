def rag_node(state: dict) -> dict:
    return {
        "law_list": [],
        "needs_visual_review": state.get("needs_visual_review", False),
    }
