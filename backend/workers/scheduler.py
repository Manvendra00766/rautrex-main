from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.logger import logger
from services.streaming_engine import streaming_engine
from services.alert_monitor import check_price_alerts
import asyncio

class BackgroundWorker:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        # Start streaming engine loop
        asyncio.create_task(streaming_engine.start())
        
        # Schedule price alert checker every 1 minute
        self.scheduler.add_job(
            self.safe_job(check_price_alerts), 
            'interval', 
            minutes=1, 
            id='check_alerts', 
            replace_existing=True
        )
        
        # Add a job to cleanup stale websocket channels or caches
        self.scheduler.add_job(
            self.safe_job(self.cleanup_task), 
            'interval', 
            hours=1, 
            id='cleanup_task', 
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Background workers started.")

    def stop(self):
        asyncio.create_task(streaming_engine.stop())
        self.scheduler.shutdown()
        logger.info("Background workers stopped.")

    def safe_job(self, func):
        """Wrapper to catch and log exceptions in background jobs."""
        async def wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background job {func.__name__} failed: {e}")
        return wrapper

    async def cleanup_task(self):
        logger.info("Running background cleanup tasks...")
        # Implementation for clearing old cache keys, old notifications, etc.

worker = BackgroundWorker()
