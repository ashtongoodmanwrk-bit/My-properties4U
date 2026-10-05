import logging
import sys

from apscheduler.schedulers.blocking import BlockingScheduler

from app import jobs
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")


def run_job(fn):
    def wrapper():
        with SessionLocal() as db:
            count = fn(db)
        logger.info("%s processed %s rows", fn.__name__, count)

    wrapper.__name__ = fn.__name__
    return wrapper


OVERDUE = run_job(jobs.mark_overdue)
REMINDERS = run_job(jobs.send_reminders)


def main():
    if "--once" in sys.argv:
        OVERDUE()
        REMINDERS()
        return

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(OVERDUE, "cron", hour=0, minute=5)
    scheduler.add_job(REMINDERS, "cron", hour=9, minute=0)
    OVERDUE()  # catch up straight away if the worker was down
    REMINDERS()
    logger.info("Worker started; jobs run daily")
    scheduler.start()


if __name__ == "__main__":
    main()
