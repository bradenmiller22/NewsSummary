"""Run the daily pipeline. Owner: Eric (scheduler).

  python scripts/run_daily.py            # run once now
  python scripts/run_daily.py --schedule # run every day at 6:00 AM local time
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import pipeline
from app.db import init_db


def run_once():
    init_db()
    digests = pipeline.run_daily()
    print(f"Built {len(digests)} digest(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true")
    args = parser.parse_args()

    if args.schedule:
        from apscheduler.schedulers.blocking import BlockingScheduler
        sched = BlockingScheduler()
        sched.add_job(run_once, "cron", hour=6, minute=0)
        print("Scheduler running; daily at 06:00. Ctrl+C to stop.")
        sched.start()
    else:
        run_once()
