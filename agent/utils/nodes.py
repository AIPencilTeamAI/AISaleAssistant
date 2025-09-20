from typing import Any
from langchain_core.messages import HumanMessage
from .state import State
from .memory import RedisSaver


async def start_node(state: State, redis: RedisSaver):
    raw_input = state["raw_input"]
    thread_id = raw_input["thread_id"]
    sender = raw_input["sender"]
    status = raw_input["status"]
    content = raw_input["content"]

    if status == "off":
        redis.list_history(key= thread_id, message= f"{sender}: {content}")
    if status == "on":
        history = redis.get_history(key=thread_id)
        state["messages"] = HumanMessage(f"Chat History: {history}")
    return state

def router(state: State):
    status = state["raw_input"]["status"]
    if status == "on":
        return "suggestion"
    return "__end__"

async def suggestion(state: State, llm_with_tools):
    response = await llm_with_tools.ainvoke({"messages": state["messages"]})
    return {"messages": [response]}
