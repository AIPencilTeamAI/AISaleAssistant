import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from .utils.tools import get_product_information, find_product_name, tone_analyzer
from .utils.state import State
from .utils.nodes import start_node, router, suggestion
from functools import partial

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def create_graph(redis):
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

    tools = [get_product_information, find_product_name, tone_analyzer]
    llm_with_tools = prompt_template | llm.bind_tools(tools)
    tool_node = ToolNode(tools) #END (if condition)

    #Building graphs
    graph_builder = StateGraph(State)
    graph_builder.add_node("start_node", partial(start_node, redis=redis))
    graph_builder.add_node("suggestion", partial(suggestion, llm_with_tools=llm_with_tools))
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
    return graph
