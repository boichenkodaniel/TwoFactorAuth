import json
import os
from typing import Any, Optional

import redis


class RedisClient:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self._client: Optional[redis.Redis] = None

    def get_redis(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )
        return self._client

    def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        try:
            redis_client = self.get_redis()
            serialized = json.dumps(value)
            if ex:
                redis_client.setex(key, ex, serialized)
            else:
                redis_client.set(key, serialized)
            return True
        except Exception:
            return False

    def get_json(self, key: str) -> Optional[Any]:
        try:
            redis_client = self.get_redis()
            data = redis_client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except Exception:
            return None

    def delete(self, key: str) -> bool:
        try:
            redis_client = self.get_redis()
            redis_client.delete(key)
            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        try:
            redis_client = self.get_redis()
            return redis_client.exists(key) > 0
        except Exception:
            return False


redis_client = RedisClient()
