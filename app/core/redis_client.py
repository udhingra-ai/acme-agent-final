import redis
from core.config import REDIS_URL
r = redis.from_url(REDIS_URL, decode_responses=True)
