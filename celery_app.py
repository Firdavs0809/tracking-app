"""Celery application (broker/result: Redis). Run: celery -A celery_app worker -l info"""

import os

from celery import Celery

broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend = os.environ.get("CELERY_RESULT_BACKEND", broker)

app = Celery(
    "shipment_tracking",
    broker=broker,
    backend=backend,
    include=["tasks.email_tasks"],
)

app.conf.update(
    task_default_queue="default",
    task_routes={
        "tasks.email_tasks.*": {"queue": "default"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={},
)
