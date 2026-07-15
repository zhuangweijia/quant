import asyncio
import json
from collections.abc import Callable
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class EventBus:
    TOPIC_ANALYSIS_PROGRESS = "analysis:progress"
    TOPIC_RANKING_READY = "analysis:ranking_ready"
    TOPIC_DATA_SYNC_ALERT = "data_sync:alert"

    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._handlers: dict[str, list[Callable]] = {}
        self._listener_task: asyncio.Task | None = None

    async def connect(self):
        settings = get_settings()
        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=True,
        )
        self._pubsub = self._redis.pubsub()
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("event_bus.connected")

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("event_bus.disconnected")

    async def publish(self, topic: str, data: dict):
        if self._redis:
            await self._redis.publish(topic, json.dumps(data, default=str))

    async def subscribe(self, topic: str, handler: Callable[[dict], Any]):
        if topic not in self._handlers:
            self._handlers[topic] = []
            if self._pubsub:
                await self._pubsub.subscribe(topic)
        self._handlers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: Callable | None = None):
        if handler and topic in self._handlers:
            self._handlers[topic] = [h for h in self._handlers[topic] if h != handler]
        else:
            self._handlers.pop(topic, None)
            if self._pubsub:
                await self._pubsub.unsubscribe(topic)

    async def _listen(self):
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    topic = message["channel"]
                    if isinstance(topic, bytes):
                        topic = topic.decode()
                    data = json.loads(message["data"])
                    for handler in self._handlers.get(topic, []):
                        try:
                            result = handler(data)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.error(
                                "event_handler_error",
                                topic=topic,
                                error=str(e),
                            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("event_bus_listen_error", error=str(e))


event_bus = EventBus()
