
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from redis.exceptions import RedisError

from app.core.redis_client import redis_client

T = TypeVar("T", bound=BaseModel)

CACHE_TTL = 300  # 5 minutes


def get_cached_response(key: str, schema: type[T],) -> T | None:
    try:
        cached_data = redis_client.get(key)

        if cached_data is None:
            return None

        return schema.model_validate_json(cached_data)

    except (RedisError, ValidationError):
        return None


def set_cached_response(key: str, response: BaseModel,) -> None:
    try:
        redis_client.setex(key, CACHE_TTL, response.model_dump_json(),)
    except RedisError:
        pass


def invalidate_employee_cache() -> None:
    try:
        for key in redis_client.scan_iter(match="employees:*"):
            redis_client.delete(key)
    except RedisError:
        pass


def invalidate_service_book_notification_cache(employee_id: int) -> None:
    try:
        redis_client.delete(f"scanned_sb:notification:{employee_id}")
    except RedisError:
        pass