import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "fleetcode_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],
)

celery.conf.update(
    task_track_started=True,
    result_expires=3600,
    timezone="UTC",
)

celery.conf.beat_schedule = {
    "refresh-cookies-every-day": {
        "task": "tasks.refresh_leetcode_cookies",
        "schedule": crontab(hour=2, minute=0),
    },
}