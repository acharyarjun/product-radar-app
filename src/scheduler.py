"""APScheduler entry for daily runs."""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from src.config import AppConfig


def run_scheduled_loop(cfg: AppConfig, job) -> None:
    tz = cfg.schedule.timezone
    hh, mm = cfg.schedule.daily_run_time.split(":")
    hour, minute = int(hh), int(mm)
    sched = BlockingScheduler(timezone=tz)
    sched.add_job(
        job,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="product_radar_daily",
        replace_existing=True,
    )
    logger.info("Scheduler started: daily at {} ({})", cfg.schedule.daily_run_time, tz)
    sched.start()