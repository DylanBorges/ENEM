import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "enem_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "worker.tasks_omr",
        "worker.tasks_reports",
        "worker.tasks_calibration",
        "worker.tasks_essay",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutos
)
