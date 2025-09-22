from langchain_core.tools import tool
from langchain_ollama import OllamaEmbeddings
import asyncpg
import httpx
import json
import os
from dotenv import load_dotenv
load_dotenv()
OLLAMA_URL=os.getenv("OLLAMA_URL")

embeddings = OllamaEmbeddings(model="bge-m3:latest",
                              base_url=os.getenv("OLLAMA_HOST"))

@tool("get_product_information")
async def get_product_information(product_name):
    """
    Queries the RAG (Retrieval-Augmented Generation) system to retrieve and generate an answer based on the input question.
    Its contain all product_information.
    Args:
        product_name (str): Product name(In vietnamese).
    Returns:
        str: JSON string containing the generated answer based on retrieved relevant information with rank of similarity.
    """
    conn_vectorstore = await asyncpg.connect(host=os.getenv("PG_HOST"), database=os.getenv("PG_DBNAME"), user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"))
    vector = str(embeddings.embed_query(product_name))

    # đổi placeholder từ %s thành $1
    results = await conn_vectorstore.fetch(
        """SELECT name, description, price FROM product_information
                        ORDER BY name_embedded <=> $1::vector
                        LIMIT 1""", vector
    )
    await conn_vectorstore.close()
    product = {"name": results[0][0], "description": results[0][1], "price": results[0][2]}
    return json.dumps(product, ensure_ascii=False, indent=0)

@tool("find_product_name")
async def find_product_name(description):
    """
    Queries the RAG (Retrieval-Augmented Generation) system to retrieve and generate an answer based on the input question.
    Its contain all information about product description to find product name.

    Args:
        text (str): The input question or query to be searched in Vietnamese.
    Returns:
        str: JSON string containing the generated answer based on retrieved relevant information with rank of similarity.
    """
    conn_vectorstore = await asyncpg.connect(host=os.getenv("PG_HOST"), database=os.getenv("PG_DBNAME"), user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"))
    vector = str(embeddings.embed_query(description))

    # đổi placeholder từ %s thành $1
    results = await conn_vectorstore.fetch(
        """SELECT name, description, price FROM product_information
                        ORDER BY description_embedded <=> $1::vector
                        LIMIT 1""", vector
    )
    await conn_vectorstore.close()
    product = {"name": results[0][0], "description": results[0][1], "price": results[0][2]}
    return json.dumps(product, ensure_ascii=False, indent=0)



from langchain_ollama import OllamaEmbeddings
async def knowledge_enriching(question:str, answer:str):
    """
    This function combine the question from user with answer from saler and push into vector store for chatbot.

    Args:
        question (str): Question from user
        answer (str): Answer from saler
    """
    embedding = OllamaEmbeddings(model = "bge-m3:latest")
    #content = gemini(content)
    vector = str(embedding.embed_query(question))
    connection = await asyncpg.connect(host=os.getenv("PG_HOST"), database=os.getenv("PG_DBNAME"), user=os.getenv("PG_USER"), password=os.getenv("PG_PASSWORD"))
    await connection.execute("INSERT INTO vector_store (question, embedding, answer) VALUES ($1, $2, $3)", question, vector, answer)
    await connection.close()

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
llm = ChatOllama(model = "qwen3:4b",
                temperature = 0.1,
                top_k = 10,
                top_p = 0.1,
                base_url=OLLAMA_URL
                ).with_structured_output(None, method="json_mode")
@tool("tone_analyzer")
async def tone_analyzer(text: str):
    """
    Extract information from user converation.
    Args:
        text (str): customer text
    Returns:
        dict: User's information
    """
    messages = [
        SystemMessage("You are highly intelligent and accurate sentiment analyzer. Analyze the sentiment of the provided text. " \
        "Categorize it into one of the following: Friendly, Indifferent, Impatient, Frustrated. Only output final answer, do not explain"),
        HumanMessage(text),
    ]
    tone = await llm.ainvoke(messages)
    return json.dumps(tone, ensure_ascii=False, indent=0)

if __name__ == "__main__":
    import asyncio
    #a = asyncio.run(knowledge_enriching("Học phí học MOS tại Tinz", "Miễn phí"))
    #print(tone_analyzer("Customer: "))
    a = asyncio.run(get_product_information("Gaming Mouse"))
    print(a)