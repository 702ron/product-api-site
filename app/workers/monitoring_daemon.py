"""
Price monitoring daemon for periodic price checks.
Runs independently to check monitor prices and send alerts.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.services.monitoring_service import monitoring_service
from app.core.logging_config import setup_logging, get_logger

logger = get_logger(__name__)


class MonitoringDaemon:
    """Daemon for periodic price monitoring."""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval  # seconds
        self.is_running = False
        self.total_checks = 0
        self.total_errors = 0
        self.started_at: Optional[datetime] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False
    
    async def start(self):
        """Start the monitoring daemon."""
        logger.info("Starting price monitoring daemon")
        self.is_running = True
        self.started_at = datetime.utcnow()
        
        try:
            while self.is_running:
                cycle_start = datetime.utcnow()
                
                try:
                    # Check monitor prices
                    await monitoring_service.check_monitor_prices(limit=100)
                    self.total_checks += 1
                    
                    cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
                    logger.debug(f"Monitoring cycle completed in {cycle_time:.2f}s")
                    
                except Exception as e:
                    self.total_errors += 1
                    logger.error(f"Error in monitoring cycle: {str(e)}")
                
                # Calculate sleep time to maintain interval
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                sleep_time = max(0, self.check_interval - cycle_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                # Log stats periodically
                if self.total_checks % 10 == 0:
                    uptime = (datetime.utcnow() - self.started_at).total_seconds()
                    logger.info(f"Monitoring daemon stats: {self.total_checks} cycles, "
                              f"{self.total_errors} errors, {uptime:.0f}s uptime")
            
            logger.info("Price monitoring daemon stopped gracefully")
            
        except Exception as e:
            logger.error(f"Fatal error in monitoring daemon: {str(e)}")
            raise
    
    def get_stats(self) -> dict:
        """Get daemon statistics."""
        uptime = (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0
        
        return {
            "is_running": self.is_running,
            "total_checks": self.total_checks,
            "total_errors": self.total_errors,
            "uptime_seconds": uptime,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "check_interval": self.check_interval
        }


async def run_monitoring_daemon(check_interval: int = None):
    """Run the monitoring daemon."""
    if not check_interval:
        check_interval = getattr(settings, 'monitoring_check_interval', 60)
    
    # Setup logging
    setup_logging()
    
    daemon = MonitoringDaemon(check_interval)
    
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Monitoring daemon interrupted by user")
    except Exception as e:
        logger.error(f"Monitoring daemon failed: {str(e)}")
        sys.exit(1)


async def main():
    """Main entry point for monitoring daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Amazon Product Intelligence Platform Monitoring Daemon")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    await run_monitoring_daemon(args.interval)


if __name__ == "__main__":
    asyncio.run(main())