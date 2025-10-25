from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import Optional
from agent.utils.memory import RedisSaver
from agent.agent import create_graph
load_dotenv()
 
RedisSaver.initialize_pool(host = os.getenv("REDIS_HOST"))
redis = RedisSaver()
graph = create_graph(redis)

class AISaleAssistant(BaseModel):
    username: Optional[str]
    content: Optional[str]
    threadID: Optional[str]
    history: Optional[str]

from agent.utils.memory_check import redis_memoryCheck, mongo_memoryCheck, memory_cache
app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/assistant")
async def chat_endpoint(request: AISaleAssistant):
    sender = request.sender
    content = request.content
    thread_id = request.threadID
    status = request.status.lower()
    
    graph_input = {"raw_input": {"sender": sender, "content": content, "thread_id": thread_id, "status": status}}

    async for chunk in graph.astream(
        graph_input,
        stream_mode="updates"
    ):
        answer = ""
        #event = await graph.aget_state(config)
        print(chunk)
    try:
        answer = chunk["suggestion"]["messages"][-1].content
    except:
        pass

    #memory_cache(user_message, answer, request.thread_id)
    return {"answer" : answer}

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
