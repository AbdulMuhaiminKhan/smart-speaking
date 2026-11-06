"""RQ queue access. The API enqueues; the worker process runs app.worker.jobs."""

from functools import lru_cache
from typing import Protocol

from redis import Redis
from rq import Queue

from app.config import get_settings

QUEUE_NAME = "analysis"


class Enqueuer(Protocol):
    def __call__(self, session_id: str) -> None: ...


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis())


def enqueue_analysis(session_id: str) -> None:
    get_queue().enqueue(
        "app.worker.jobs.analyze_session",
        session_id,
        job_id=f"analyze-{session_id}",
        job_timeout=get_settings().job_timeout_s,
        result_ttl=3600,
        failure_ttl=24 * 3600,
    )


def get_enqueuer() -> Enqueuer:
    """FastAPI dependency so tests can swap in a fake."""
    return enqueue_analysis
