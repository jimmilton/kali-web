"""Celery application configuration.

Copyright 2025 milbert.ai
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "kwebbie",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "worker.tasks.tool_tasks",
        "worker.tasks.workflow_tasks",
        "worker.tasks.report_tasks",
        "worker.tasks.notification_tasks",
        "worker.tasks.parse_results",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=86400,  # 24 hours max
    task_soft_time_limit=82800,  # 23 hours soft limit
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "worker.tasks.tool_tasks.*": {"queue": "tools"},
        "worker.tasks.workflow_tasks.*": {"queue": "workflows"},
        "worker.tasks.report_tasks.*": {"queue": "reports"},
        "worker.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "worker.tasks.tool_tasks.cleanup_old_jobs",
            "schedule": 3600.0,  # Every hour
        },
        "process-scheduled-jobs": {
            "task": "worker.tasks.tool_tasks.process_scheduled_jobs",
            "schedule": 60.0,  # Every minute
        },
    },
)
