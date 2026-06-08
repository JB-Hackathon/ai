from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from .nodes.chatbot import chatbot_node
from .nodes.tools import expression_edit, law_review
from .state import ChatState

_tools = [law_review, expression_edit]


def should_continue(state: ChatState) -> str:
    if state["messages"][-1].tool_calls:
        return "tools"
    return END


def build_graph(checkpointer=None):
    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    builder = StateGraph(ChatState)
    builder.add_node("chatbot_node", chatbot_node)
    builder.add_node("tools", ToolNode(_tools))

    builder.add_edge(START, "chatbot_node")
    builder.add_conditional_edges(
        "chatbot_node",
        should_continue,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "chatbot_node")

    return builder.compile(checkpointer=checkpointer)


graph = build_graph()
