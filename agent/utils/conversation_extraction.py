from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
import dotenv
import os
def conversation_extraction(psid: str):
    """
    Extract information from user converation.
    Args:
        psid (str): user if
    Returns:
        dict: User's information
    """
    llm = ChatOllama(model = "qwen3:4b",
                temperature = 0.1,
                top_k = 10,
                top_p = 0.1,
                base_url=os.getenv("OLLAMA_HOST")
                ).with_structured_output(None, method="json_mode")

    with open(f"./memory_cache/{psid}.txt", "r", encoding = "utf-8") as manager:
        history = manager.read()
    messages = [
        SystemMessage("You are an expert extraction algorithm. Extract all user's information from the converation(user: ), not the bot response"),
        HumanMessage(history),
    ]
    raw_result = llm.invoke(messages)
    raw_result.update({"psid":psid})
    return raw_result

if __name__ == "__main__":
    print(conversation_extraction("test"))  
    