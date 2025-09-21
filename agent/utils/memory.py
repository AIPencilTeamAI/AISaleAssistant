import redis

class RedisSaver:
    _pool = None 
    @classmethod
    def initialize_pool(cls, host='localhost', port=6379, db=0, decode_responses=True):
        if cls._pool is None:
            print("Initializing the shared connection pool for RedisSaver...")
            cls._pool = redis.ConnectionPool(
                host=host, 
                port=port, 
                db=db, 
                decode_responses=decode_responses
            )
    def __init__(self):
        if RedisSaver._pool is None:
            RedisSaver.initialize_pool()
        self.client = redis.Redis(connection_pool=RedisSaver._pool)
    
    def get_message(self, key):
        return self.client.get(key)
    
    def append_message(self, key, message):
        if self.client.exists(key):
            self.client.append(key, message)
        else:
            self.client.set(key, message)
            self.client.expire(key, 60)
    
    def del_message(self, key):
        self.client.delete(key)
    
    def list_history(self, key, message, windows_length = 10):
        llen = self.client.llen(key)
        if llen < windows_length:
             self.client.rpush(key, message)
        else:
            if llen - windows_length > 1:
                while llen >= windows_length:
                    self.client.lpop(key)
                    llen = self.client.llen(key)
            else:
                self.client.lpop(key)
            self.client.rpush(key, message)
    
    def get_history(self, key):
        return " ".join(self.client.lrange(key, 0, -1))
    

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    RedisSaver.initialize_pool(host = os.getenv("REDIS_HOST"))
    redis = RedisSaver()
    #for i in range(10):
        #a = asyncio.run(redis.list_history("hello", i))
    #a = asyncio.run(redis.list_history("hello", "sjddjd",5))
    a = redis.get_history("test_3")
    print(type(a))