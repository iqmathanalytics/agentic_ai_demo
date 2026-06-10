def describe_langgraph_workflow(nodes: list[str]) -> dict:
    """Small metadata helper; agent execution uses explicit streaming for UI control."""
    try:
        from langgraph.graph import END, StateGraph
        from typing_extensions import TypedDict

        class GraphState(TypedDict, total=False):
            current: str

        graph = StateGraph(GraphState)
        for node in nodes:
            graph.add_node(node, lambda state, node=node: {"current": node})
        graph.set_entry_point(nodes[0])
        for left, right in zip(nodes, nodes[1:]):
            graph.add_edge(left, right)
        graph.add_edge(nodes[-1], END)
        graph.compile()
        return {"engine": "langgraph", "nodes": nodes}
    except Exception:
        return {"engine": "explicit-async", "nodes": nodes}

