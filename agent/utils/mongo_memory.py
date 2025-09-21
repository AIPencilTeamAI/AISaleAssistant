import asyncio
from watchfiles import awatch
import os
from agent.utils.conversation_extraction import conversation_extraction
import redis
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

async def mongo_push(file_path: str) ->None:
    """
    Push dict into MongoDB
    Args:
        file_path(str): file path
    """
    print(f"Waiting {file_path}")
    await asyncio.sleep(900) #time set
    file_name = os.path.basename(file_path)
    psid = file_name.strip(".txt")
    user_info = conversation_extraction(psid)
    
    print(f"Pushing into MongoDB {file_path}")
    m_client = MongoClient(os.getenv("MONGO_URL"))
    m_database = m_client.get_database(os.getenv("MONGO_DATABASE"))
    m_history = m_database.get_collection(os.getenv("MONGO_COLLECTION"))
    m_history.insert_one(user_info)
    
    print(f"Pushed into MongoDB {file_path}")
    os.remove(file_path)
    r = redis.Redis(host=os.getenv("REDIS_HOST"), 
                    port=os.getenv("REDIS_PORT"), 
                    password=os.getenv("REDIS_PASSWORD"),
                    db= 0)
    r.delete(f'checkpoint:{psid}:')
    cp_w_keys = r.keys(f"checkpoint_write:{psid}:*")
    for key in cp_w_keys:
        r.delete(key.decode("utf-8"))
    print(f"Redis Key {psid} deleted")
async def watch_folder(folder: str):
    """
    Watch for changing (adding file) into folder
    Agrs:
        folder(str): folder path
    """
    async for changes in awatch(folder):
        for change, path in changes:
            if change.name == "added":
                print(changes)
                asyncio.create_task(mongo_push(path))

if __name__ == "__main__":
    print("Started!")
    folder_to_watch = "./memory_cache"
    asyncio.run(watch_folder(folder_to_watch))
