import os
from dotenv import load_dotenv
import redis
from pymongo import MongoClient
load_dotenv()

def memory_cache(user = None, bot = None, psid = None) -> None:
    """
    This function writes the conversation between user and bot into a file.
    
    Agrs:
        user (str): user messages
        bot (str): bot messages
        psid (str): user id
    """
    with open(f"./memory_cache/{psid}.txt", "a", encoding = "utf-8") as manager:
        manager.write(f"user: {user}, bot: {bot}. ")

def redis_memoryCheck(psid: str):
    """
    Check if the conversation exists in Redis.

    Args:
        psid (str): user id
    """
    r = redis.Redis(host=os.getenv("REDIS_HOST"), 
                    port=os.getenv("REDIS_PORT"), 
                    password=os.getenv("REDIS_PASSWORD"),
                    db= 0)
    checkpoint = r.exists(f"checkpoint:{psid}:")
    if checkpoint == 0:
        return False
    else:
        return True

def mongo_memoryCheck(psid: str):
    """
    Check if the conversation exists in MongoDB.

    Args:
        psid (str): user id
    Returns:
        False: if the conversation exist in MongoDB
        list(True, [history]): return the values and history in MongoDB
    """    
    m_client = MongoClient(os.getenv("MONGO_URL"))
    m_database = m_client.get_database(os.getenv("MONGO_DATABASE"))
    m_history = m_database.get_collection(os.getenv("MONGO_COLLECTION"))
    query = {"psid": psid}
    history = m_history.find_one(query)
    if history == None:
        return False
    else:
        m_history.delete_one(history)
        del history["_id"]
        del history["psid"]
        return [True, f"{history}".replace("{", "").replace("}","")]
        #return history

if __name__ == "__main__":
    tes = mongo_memoryCheck("53a293835f2043ac8307362f6d3c230f")
    #del mongfofofof["_id"]
    #del mongfofofof["psid"]
    print(tes)
    print(type(tes))
    