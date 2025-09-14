from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph import add_messages
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.checkpoint.redis.ashallow import AsyncShallowRedisSaver
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import asyncio
from anyio.to_thread import run_sync
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, AnyMessage
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import ToolMessage
from Tools import get_product_information, find_product_name, tone_analyzer
from memory import RedisSaver
tools = [get_product_information, find_product_name, tone_analyzer]
load_dotenv()

RedisSaver.initialize_pool(host = os.getenv("REDIS_HOST"))
redis = RedisSaver()

api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key)

"""llm = ChatOllama(model = "qwen3:14b",
                temperature = 0.1,
                top_k = 10,
                top_p = 0.2,
                base_url=os.getenv("OLLAMA_HOST"))"""

with open('./prompt_template.txt', 'r', encoding='utf-8') as f:
    SYSTEM_PROMPT = f.read()
prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="messages")
])

llm_with_tools = prompt_template | llm.bind_tools(tools)

#State
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages] #give bot what is going on in the main chat
    raw_input: dict
    
async def start_node(state: State):
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

async def suggestion(state: State):
    response = await llm_with_tools.ainvoke({"messages": state["messages"]})
    return {"messages": [response]}

tool_node = ToolNode(tools) #END (if condition)

#Building graphs
graph_builder = StateGraph(State)
graph_builder.add_node("start_node", start_node)
graph_builder.add_node("suggestion", suggestion)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "start_node")
graph_builder.add_conditional_edges("start_node",
                                    router,
                                    {"suggestion":"suggestion",
                                     "__end__":"__end__"}
                                    )
graph_builder.add_conditional_edges("suggestion",
                                    tools_condition,
                                    {"tools":"tools", "__end__":"__end__"}
                                    )
graph_builder.add_edge("tools", "suggestion")

graph = graph_builder.compile()

class AISaleAssistant(BaseModel):
    sender: Optional[str]
    content: Optional[str]
    thread_id: Optional[str]
    status: Optional[str]

from memory_check import redis_memoryCheck, mongo_memoryCheck, memory_cache
app = FastAPI()

@app.post("/chat")
async def chat_endpoint(request: AISaleAssistant):
    sender = request.sender
    content = request.content
    thread_id = request.thread_id
    status = request.status.lower()
    
    graph_input = {"raw_input": {"sender": sender, "content": content, "thread_id": thread_id, "status": status}}

    async for chunk in graph.astream(
        graph_input,
        stream_mode="updates"
    ):
        answer = ""
        try:
            answer = list(chunk.values())[-1]["messages"][-1].content
        except TypeError: #Tool
            pass
        #event = await graph.aget_state(config)
        print(chunk)
    
    #memory_cache(user_message, answer, request.thread_id)
    return answer


#   ainvoke dung cho production
#   result = await graph.ainvoke(graph_input, config)
#   messages = result.get("messages", [])
#   assistant = messages[-1].content if messages else ""
#   answer = assistant.split("</think>")[-1].replace("\n", " ").strip()
#   return Answer

    
# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8400)
