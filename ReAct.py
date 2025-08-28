from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph import add_messages
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import tools_condition
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
tools = [get_product_information, find_product_name, tone_analyzer]
load_dotenv()

"""api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key)"""

llm = ChatOllama(model = "qwen3:14b",
                temperature = 0.1,
                top_k = 10,
                top_p = 0.2,
                base_url=os.getenv("OLLAMA_HOST"))
llm_with_tools = llm.bind_tools(tools)

#State
class State(TypedDict):
    main_chat: list
    internal_chat: list
    raw_input: dict
    suggestion: Optional[str]
    feedback: Optional[str]

async def start_node(state: State):
    raw_input = state["raw_input"]
    if raw_input["chat_type"] == "main":
        if raw_input["sender"] == "customer":
            state["main_chat"].append({"role": "human", "content": raw_input["content"]})
        else:
            state["main_chat"].append({"role": "human", "content": raw_input["content"]})
    else:
        state["internal_chat"].append({"role": "human", "content": raw_input["content"]})
    return state

def router(state: State):
    raw_input = state["raw_input"]
    if raw_input["chat_type"] == "main":
        if raw_input["sender"] == "customer":
            return "main_customer"
        else:
            return "main_salerperson"
    elif raw_input["chat_type"] == "internal":
        return "internal"
    return "__end__"

async def main_chat_customer(state: State):
    customer_message = state["main_chat"][-1]["content"]
    prompt = f"""
    Phân tích tin nhắn của customer: {customer_message}
    trong ngữ cảnh cuộc hội thoại: {state["main_chat"]}
    Hãy đưa ra gợi ý cho salesperson để phản hồi. Sử dụng tools nếu cần để lấy thông tin sản phẩm hoặc phân tích ngữ điệu.
    """
    suggestion = llm_with_tools.invoke(prompt)
    state["suggestion"] = suggestion
    return state

async def main_chat_salesperson(state: State):
    salesperson_message = state["main_chat"][-1]["content"]
    prompt = f"""
    Đánh giá phản hồi của salesperson: {salesperson_message}
    trong ngữ cảnh: {state["main_chat"]}
    Hãy đưa ra nhận xét để cải thiện hiệu quả giao tiếp.
    """
    feedback = llm_with_tools.invoke(prompt)
    state["feedback"] = feedback
    return state

async def internal_chat(state: State):
    salesperson_message = state["internal_chat"][-1]["content"]
    prompt = f"""
    Salesperson hỏi: {salesperson_message}
    Dựa trên cuộc hội thoại với customer: {state["main_chat"]}
    Hãy trả lời và hỗ trợ salesperson với thông tin cần thiết. Sử dụng tools nếu cần.
    """
    response = llm_with_tools.invoke(prompt)
    # Thêm phản hồi của AI vào internal_chat
    state["internal_chat"].append({"role": "ai", "content": response})
    return state

class ToolNode:
    """A node that runs the tools requested in the last AIMessage."""
    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}
    async def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        psid = inputs.get("psid")
        for tool_call in message.tool_calls:
            #Muc dich la de lay dua message id vao ben trong parameter, de khi can, co the lay duoc username
            tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}
tool_node = ToolNode(tools) #END (if condition)

#Building graphs
graph_builder = StateGraph(State)
graph_builder.add_node("start_node", start_node)
graph_builder.add_node("main_chat_customer", main_chat_customer)
graph_builder.add_node("main_chat_salesperson", main_chat_salesperson)
graph_builder.add_node("internal_chat", internal_chat)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "start_node")
graph_builder.add_conditional_edges("start_node",
                                    router,
                                    {"main_customer":"main_chat_customer",
                                     "main_salesperson":"main_chat_salesperson",
                                     "internal":"internal_chat",
                                     "__end__":"__end__"}
                                    )
graph_builder.add_conditional_edges("main_chat_customer",
                                    tools_condition,
                                    {"tools":"tools", "__end__":"__end__"}
                                    )
graph_builder.add_conditional_edges("main_chat_salesperson",
                                    tools_condition,
                                    {"tools":"tools", "__end__":"__end__"}
                                    )
graph_builder.add_conditional_edges("internal_chat",
                                    tools_condition,
                                    {"tools":"tools", "__end__":"__end__"}
                                    )


#Checkpoint (History)
async def asyncredis():
    global graph
    async with AsyncShallowRedisSaver.from_conn_string(os.getenv("REDIS_URL")) as checkpointer:
        await checkpointer.setup()
        graph = graph_builder.compile(checkpointer=checkpointer)


class AISaleAssistant(BaseModel):
    chat_type: str
    sender: str
    content: str
    thread_id: str

from memory_check import redis_memoryCheck, mongo_memoryCheck, memory_cache
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await asyncredis()

@app.post("/chat")
async def chat_endpoint(request: AISaleAssistant):
    chat_type = request.chat_type
    sender = request.sender
    content = request.content
    thread_id = request.thread_id
    config = {"configurable": {"thread_id": thread_id}}
    graph_input = {"raw_input": {"chat_type": chat_type ,"sender": sender, "content": content}}
    isRedis = redis_memoryCheck(request.thread_id)
    isMongo = mongo_memoryCheck(request.thread_id)
    if not isRedis and not isMongo: #uu tien Redis, vi neu ton tai ca hai thi phai lay tu redis trc
        pass
    elif isRedis:
        pass
    elif isMongo[0] and not isRedis:
        memory_cache(user = isMongo[1], psid = request.thread_id)
        graph_input.update({"messages": [{"role":"system", "content": isMongo[1]}]}) 


    async for chunk in graph.astream(
        graph_input, config,
        stream_mode="updates"
    ):
        try:
            answer = chunk["chatbot"]["messages"][-1].content.split("</think>")[-1].replace("\n", " ").strip()
        except KeyError: #Tool
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
