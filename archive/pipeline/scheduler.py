"""
scheduler.py — Keeps the pipeline running on a daily schedule.
"""

import logging
import os
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def start_scheduler(pipeline_fn) -> None:
    """
    Start a blocking scheduler that calls pipeline_fn daily at SCHEDULE_TIME.
    SCHEDULE_TIME env var format: "HH:MM" (24-hour, e.g. "06:00")
    """
    schedule_time = os.getenv("SCHEDULE_TIME", "06:00")
    hour, minute = schedule_time.split(":")

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        pipeline_fn,
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        id="daily_pipeline",
        name="Daily Briefer pipeline",
        replace_existing=True,
        misfire_grace_time=3600,  # if it missed by up to 1h, still run it
    )

    logger.info(f"Scheduler running — pipeline fires daily at {schedule_time} UTC")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
