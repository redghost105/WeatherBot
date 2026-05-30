#!/usr/bin/env python3
"""
Automated scheduler for daily WeatherPredictor execution.

Runs kalshi_predictor_live.py on a schedule (default: daily at 9 AM UTC).

Usage:
    python3 scheduler.py              # Run once immediately
    python3 scheduler.py --daily      # Run daily at 9 AM UTC
    python3 scheduler.py --hourly     # Run every hour
"""

import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_predictor():
    """Execute kalshi_predictor_live.py and log results."""
    logger.info("=" * 80)
    logger.info("Starting WeatherPredictor execution...")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 80)

    try:
        result = subprocess.run(
            ["python3", "kalshi_predictor_live.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info("✅ Execution completed successfully")
            # Print last 50 lines of output
            lines = result.stdout.split('\n')
            logger.info("Output summary:")
            for line in lines[-50:]:
                if line.strip():
                    logger.info(f"  {line}")
        else:
            logger.error(f"❌ Execution failed with code {result.returncode}")
            logger.error(f"Error output:\n{result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("❌ Execution timed out after 5 minutes")
    except Exception as e:
        logger.error(f"❌ Execution failed: {e}")

    logger.info("=" * 80)


def schedule_daily(hour=9, minute=0):
    """
    Schedule daily execution at specified UTC time.

    Args:
        hour: Hour in UTC (0-23, default 9 = 9 AM UTC)
        minute: Minute (0-59, default 0)

    Usage:
        schedule_daily(9, 0)  # Daily at 9 AM UTC
    """
    import schedule
    import time

    schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(run_predictor)

    logger.info(f"Scheduler active. Will run daily at {hour:02d}:{minute:02d} UTC")
    logger.info("(Press Ctrl+C to stop)")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


def setup_cron_job():
    """
    Alternative: Setup Linux cron job for automation (no schedule library needed).

    Cron syntax: minute hour day month day-of-week command

    Examples:
        # Daily at 9 AM UTC
        0 9 * * * /usr/bin/python3 /path/to/kalshi_programs/Polymarket/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1

        # Every 6 hours
        0 */6 * * * /usr/bin/python3 /path/to/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1

        # Every hour
        0 * * * * /usr/bin/python3 /path/to/kalshi_predictor_live.py >> /tmp/kalshi.log 2>&1

    To add to crontab:
        crontab -e
        # Then paste the line above
    """
    script_path = Path(__file__).parent / "kalshi_predictor_live.py"
    log_path = Path("/tmp/kalshi.log")

    cron_line = f"0 9 * * * /usr/bin/python3 {script_path} >> {log_path} 2>&1"

    logger.info("Cron job setup instructions:")
    logger.info("=" * 80)
    logger.info("1. Open crontab editor:")
    logger.info("   crontab -e")
    logger.info("")
    logger.info("2. Add this line for daily execution at 9 AM UTC:")
    logger.info(f"   {cron_line}")
    logger.info("")
    logger.info("3. Save and exit (Ctrl+X in nano, :wq in vim)")
    logger.info("")
    logger.info("4. Verify it's installed:")
    logger.info("   crontab -l")
    logger.info("=" * 80)


if __name__ == "__main__":
    if "--daily" in sys.argv:
        try:
            import schedule
            schedule_daily(hour=9, minute=0)  # 9 AM UTC
        except ImportError:
            logger.error("schedule library not installed. Install with: pip install schedule")
            logger.info("\nAlternative: Use cron job instead")
            setup_cron_job()

    elif "--hourly" in sys.argv:
        try:
            import schedule
            schedule.every().hour.do(run_predictor)
            logger.info("Scheduler active. Will run every hour")
            logger.info("(Press Ctrl+C to stop)")

            import time
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")

        except ImportError:
            logger.error("schedule library not installed. Install with: pip install schedule")

    elif "--cron" in sys.argv:
        setup_cron_job()

    else:
        # Run once immediately
        run_predictor()
