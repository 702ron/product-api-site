"""
Price monitoring service for Amazon Product Intelligence Platform.
Handles price tracking, change detection, and alert generation.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.models import PriceMonitor, PriceHistory, PriceAlert, User
from app.services.amazon_service import amazon_service
from app.services.notification_service import notification_service
from app.monitoring.metrics import (
    price_monitor_checks_total, price_monitor_alerts_total, 
    price_monitor_errors_total, price_monitor_duration
)

logger = logging.getLogger(__name__)


class PriceMonitoringService:
    """Service for managing price monitoring and alerts."""
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 60  # Check every minute for monitors that need updates
        
    async def create_monitor(
        self,
        user_id: str,
        asin: str,
        name: str,
        marketplace: str = "US",
        target_price: Optional[float] = None,
        threshold_percentage: Optional[float] = None,
        monitor_frequency_minutes: int = 60,
        email_alerts: bool = True,
        webhook_url: Optional[str] = None,
        alert_conditions: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None
    ) -> PriceMonitor:
        """Create a new price monitor."""
        
        if not db:
            async with get_db_session() as db:
                return await self._create_monitor_internal(
                    user_id, asin, name, marketplace, target_price, threshold_percentage,
                    monitor_frequency_minutes, email_alerts, webhook_url, alert_conditions, db
                )
        else:
            return await self._create_monitor_internal(
                user_id, asin, name, marketplace, target_price, threshold_percentage,
                monitor_frequency_minutes, email_alerts, webhook_url, alert_conditions, db
            )
    
    async def _create_monitor_internal(
        self, user_id: str, asin: str, name: str, marketplace: str,
        target_price: Optional[float], threshold_percentage: Optional[float],
        monitor_frequency_minutes: int, email_alerts: bool, webhook_url: Optional[str],
        alert_conditions: Optional[Dict[str, Any]], db: AsyncSession
    ) -> PriceMonitor:
        """Internal method to create price monitor."""
        
        # Validate inputs
        if target_price is not None and target_price <= 0:
            raise ValueError("Target price must be positive")
        
        if threshold_percentage is not None and threshold_percentage <= 0:
            raise ValueError("Threshold percentage must be positive")
        
        if monitor_frequency_minutes < 1:
            raise ValueError("Monitor frequency must be at least 1 minute")
        
        # Check if user already has a monitor for this ASIN
        existing_query = select(PriceMonitor).where(
            and_(
                PriceMonitor.user_id == user_id,
                PriceMonitor.asin == asin,
                PriceMonitor.marketplace == marketplace,
                PriceMonitor.is_active == True
            )
        )
        existing = await db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ValueError(f"Active monitor already exists for ASIN {asin} in {marketplace}")
        
        # Create monitor
        monitor = PriceMonitor(
            user_id=user_id,
            asin=asin,
            marketplace=marketplace,
            name=name,
            target_price=target_price,
            threshold_percentage=threshold_percentage,
            monitor_frequency_minutes=monitor_frequency_minutes,
            email_alerts=email_alerts,
            webhook_url=webhook_url,
            alert_conditions=alert_conditions or {}
        )
        
        db.add(monitor)
        await db.commit()
        await db.refresh(monitor)
        
        # Get initial price
        try:
            await self._check_price_for_monitor(monitor, db)
        except Exception as e:
            logger.warning(f"Failed to get initial price for monitor {monitor.id}: {str(e)}")
        
        logger.info(f"Created price monitor {monitor.id} for user {user_id}, ASIN {asin}")
        return monitor
    
    async def get_user_monitors(
        self, 
        user_id: str, 
        active_only: bool = True,
        db: AsyncSession = None
    ) -> List[PriceMonitor]:
        """Get all monitors for a user."""
        
        if not db:
            async with get_db_session() as db:
                return await self._get_user_monitors_internal(user_id, active_only, db)
        else:
            return await self._get_user_monitors_internal(user_id, active_only, db)
    
    async def _get_user_monitors_internal(
        self, user_id: str, active_only: bool, db: AsyncSession
    ) -> List[PriceMonitor]:
        """Internal method to get user monitors."""
        
        query = select(PriceMonitor).where(PriceMonitor.user_id == user_id)
        
        if active_only:
            query = query.where(PriceMonitor.is_active == True)
        
        query = query.options(
            selectinload(PriceMonitor.price_history),
            selectinload(PriceMonitor.price_alerts)
        ).order_by(desc(PriceMonitor.created_at))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_monitor(
        self,
        monitor_id: str,
        user_id: str,
        updates: Dict[str, Any],
        db: AsyncSession = None
    ) -> PriceMonitor:
        """Update a price monitor."""
        
        if not db:
            async with get_db_session() as db:
                return await self._update_monitor_internal(monitor_id, user_id, updates, db)
        else:
            return await self._update_monitor_internal(monitor_id, user_id, updates, db)
    
    async def _update_monitor_internal(
        self, monitor_id: str, user_id: str, updates: Dict[str, Any], db: AsyncSession
    ) -> PriceMonitor:
        """Internal method to update monitor."""
        
        # Get monitor
        query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == user_id
            )
        )
        result = await db.execute(query)
        monitor = result.scalar_one_or_none()
        
        if not monitor:
            raise ValueError("Monitor not found")
        
        # Update fields
        for field, value in updates.items():
            if hasattr(monitor, field):
                setattr(monitor, field, value)
        
        monitor.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(monitor)
        
        logger.info(f"Updated monitor {monitor_id}")
        return monitor
    
    async def delete_monitor(
        self, 
        monitor_id: str, 
        user_id: str,
        db: AsyncSession = None
    ) -> bool:
        """Delete a price monitor."""
        
        if not db:
            async with get_db_session() as db:
                return await self._delete_monitor_internal(monitor_id, user_id, db)
        else:
            return await self._delete_monitor_internal(monitor_id, user_id, db)
    
    async def _delete_monitor_internal(
        self, monitor_id: str, user_id: str, db: AsyncSession
    ) -> bool:
        """Internal method to delete monitor."""
        
        # Get monitor
        query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == user_id
            )
        )
        result = await db.execute(query)
        monitor = result.scalar_one_or_none()
        
        if not monitor:
            return False
        
        # Soft delete by deactivating
        monitor.is_active = False
        monitor.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Deleted monitor {monitor_id}")
        return True
    
    async def check_monitor_prices(self, limit: int = 100):
        """Check prices for monitors that need updates."""
        
        async with get_db_session() as db:
            # Find monitors that need checking
            cutoff_time = datetime.utcnow()
            
            query = select(PriceMonitor).where(
                and_(
                    PriceMonitor.is_active == True,
                    PriceMonitor.consecutive_failures < 5,  # Skip monitors with too many failures
                    func.coalesce(
                        PriceMonitor.last_checked_at + 
                        func.make_interval(0, 0, 0, 0, 0, PriceMonitor.monitor_frequency_minutes),
                        datetime.min
                    ) <= cutoff_time
                )
            ).limit(limit)
            
            result = await db.execute(query)
            monitors = result.scalars().all()
            
            logger.info(f"Checking prices for {len(monitors)} monitors")
            
            # Process monitors concurrently
            if monitors:
                tasks = [self._check_price_for_monitor(monitor, db) for monitor in monitors]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful = sum(1 for r in results if not isinstance(r, Exception))
                failed = len(results) - successful
                
                logger.info(f"Price check completed: {successful} successful, {failed} failed")
    
    async def _check_price_for_monitor(self, monitor: PriceMonitor, db: AsyncSession):
        """Check price for a single monitor."""
        start_time = datetime.utcnow()
        
        try:
            price_monitor_checks_total.labels(
                asin=monitor.asin,
                marketplace=monitor.marketplace
            ).inc()
            
            # Get current price from Amazon API
            product_data = await amazon_service.get_product_data(
                asin=monitor.asin,
                marketplace=monitor.marketplace,
                user_id=monitor.user_id,
                db=db,
                skip_credit_check=True  # Monitor checks don't use credits
            )
            
            # Extract price information
            current_price = self._extract_price(product_data)
            availability = self._extract_availability(product_data)
            title = getattr(product_data, 'title', None)
            
            # Get previous price for comparison
            previous_price = monitor.last_price
            
            # Calculate price change
            price_change = None
            price_change_percentage = None
            if previous_price and current_price:
                price_change = current_price - previous_price
                price_change_percentage = (price_change / previous_price) * 100
            
            # Store price history
            price_history = PriceHistory(
                monitor_id=monitor.id,
                price=current_price,
                availability=availability,
                title=title,
                product_details=product_data.dict() if hasattr(product_data, 'dict') else {},
                price_change=price_change,
                price_change_percentage=price_change_percentage,
                response_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            
            db.add(price_history)
            
            # Update monitor status
            monitor.last_checked_at = datetime.utcnow()
            monitor.last_price = current_price
            monitor.consecutive_failures = 0
            
            # Check for alerts
            alerts = await self._check_alerts(monitor, current_price, previous_price, availability, db)
            
            await db.commit()
            
            # Record metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            price_monitor_duration.labels(
                asin=monitor.asin,
                marketplace=monitor.marketplace
            ).observe(processing_time)
            
            if alerts:
                price_monitor_alerts_total.labels(
                    asin=monitor.asin,
                    marketplace=monitor.marketplace
                ).inc(len(alerts))
            
            logger.debug(f"Checked price for monitor {monitor.id}: ${current_price}")
            
        except Exception as e:
            # Handle failures
            monitor.last_checked_at = datetime.utcnow()
            monitor.consecutive_failures += 1
            await db.commit()
            
            price_monitor_errors_total.labels(
                asin=monitor.asin,
                marketplace=monitor.marketplace,
                error_type=type(e).__name__
            ).inc()
            
            logger.error(f"Failed to check price for monitor {monitor.id}: {str(e)}")
            raise
    
    def _extract_price(self, product_data) -> Optional[float]:
        """Extract price from product data."""
        if hasattr(product_data, 'price') and product_data.price:
            return float(product_data.price)
        
        # Try alternative price fields
        if hasattr(product_data, 'list_price') and product_data.list_price:
            return float(product_data.list_price)
        
        return None
    
    def _extract_availability(self, product_data) -> Optional[str]:
        """Extract availability from product data."""
        if hasattr(product_data, 'availability'):
            return product_data.availability
        
        if hasattr(product_data, 'in_stock'):
            return "In Stock" if product_data.in_stock else "Out of Stock"
        
        return None
    
    async def _check_alerts(
        self, 
        monitor: PriceMonitor, 
        current_price: Optional[float],
        previous_price: Optional[float],
        availability: Optional[str],
        db: AsyncSession
    ) -> List[PriceAlert]:
        """Check if any alerts should be sent."""
        
        alerts = []
        
        if not current_price:
            return alerts
        
        # Check target price alert
        if monitor.target_price and current_price <= monitor.target_price:
            alert = await self._create_alert(
                monitor=monitor,
                alert_type="target_reached",
                message=f"Target price reached! {monitor.name} is now ${current_price:.2f} (target: ${monitor.target_price:.2f})",
                current_price=current_price,
                target_price=monitor.target_price,
                db=db
            )
            alerts.append(alert)
        
        # Check threshold percentage alert
        if (monitor.threshold_percentage and previous_price and 
            current_price < previous_price):
            
            price_drop_percentage = ((previous_price - current_price) / previous_price) * 100
            
            if price_drop_percentage >= monitor.threshold_percentage:
                alert = await self._create_alert(
                    monitor=monitor,
                    alert_type="threshold_reached",
                    message=f"Price drop alert! {monitor.name} dropped {price_drop_percentage:.1f}% to ${current_price:.2f}",
                    current_price=current_price,
                    previous_price=previous_price,
                    price_change=current_price - previous_price,
                    price_change_percentage=-price_drop_percentage,
                    db=db
                )
                alerts.append(alert)
        
        # Check availability alerts
        if availability:
            if "out of stock" in availability.lower() and monitor.last_price:
                alert = await self._create_alert(
                    monitor=monitor,
                    alert_type="out_of_stock",
                    message=f"Stock alert! {monitor.name} is now out of stock",
                    current_price=current_price,
                    db=db
                )
                alerts.append(alert)
            elif "in stock" in availability.lower() and previous_price is None:
                alert = await self._create_alert(
                    monitor=monitor,
                    alert_type="back_in_stock",
                    message=f"Stock alert! {monitor.name} is back in stock at ${current_price:.2f}",
                    current_price=current_price,
                    db=db
                )
                alerts.append(alert)
        
        # Send alerts
        for alert in alerts:
            await self._send_alert(monitor, alert, db)
        
        return alerts
    
    async def _create_alert(
        self,
        monitor: PriceMonitor,
        alert_type: str,
        message: str,
        current_price: float,
        previous_price: Optional[float] = None,
        target_price: Optional[float] = None,
        price_change: Optional[float] = None,
        price_change_percentage: Optional[float] = None,
        db: AsyncSession = None
    ) -> PriceAlert:
        """Create a price alert."""
        
        alert = PriceAlert(
            monitor_id=monitor.id,
            alert_type=alert_type,
            message=message,
            current_price=current_price,
            previous_price=previous_price,
            target_price=target_price,
            price_change=price_change,
            price_change_percentage=price_change_percentage
        )
        
        db.add(alert)
        await db.flush()  # Get the ID without committing
        
        return alert
    
    async def _send_alert(self, monitor: PriceMonitor, alert: PriceAlert, db: AsyncSession):
        """Send alert notifications."""
        
        try:
            # Send email alert
            if monitor.email_alerts:
                await notification_service.send_price_alert_email(monitor, alert)
                alert.email_sent = True
                alert.email_sent_at = datetime.utcnow()
                alert.email_delivery_status = "sent"
            
            # Send webhook alert
            if monitor.webhook_url:
                await notification_service.send_price_alert_webhook(monitor, alert)
                alert.webhook_sent = True
                alert.webhook_sent_at = datetime.utcnow()
                alert.webhook_delivery_status = "sent"
            
            # Update monitor last alert time
            monitor.last_alert_sent_at = datetime.utcnow()
            
        except Exception as e:
            alert.error_message = str(e)
            alert.email_delivery_status = "failed"
            alert.webhook_delivery_status = "failed"
            logger.error(f"Failed to send alert {alert.id}: {str(e)}")
    
    async def get_price_history(
        self,
        monitor_id: str,
        user_id: str,
        days: int = 30,
        db: AsyncSession = None
    ) -> List[PriceHistory]:
        """Get price history for a monitor."""
        
        if not db:
            async with get_db_session() as db:
                return await self._get_price_history_internal(monitor_id, user_id, days, db)
        else:
            return await self._get_price_history_internal(monitor_id, user_id, days, db)
    
    async def _get_price_history_internal(
        self, monitor_id: str, user_id: str, days: int, db: AsyncSession
    ) -> List[PriceHistory]:
        """Internal method to get price history."""
        
        # Verify user owns the monitor
        monitor_query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == user_id
            )
        )
        monitor_result = await db.execute(monitor_query)
        if not monitor_result.scalar_one_or_none():
            raise ValueError("Monitor not found")
        
        # Get price history
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(PriceHistory).where(
            and_(
                PriceHistory.monitor_id == monitor_id,
                PriceHistory.recorded_at >= cutoff_date
            )
        ).order_by(desc(PriceHistory.recorded_at))
        
        result = await db.execute(query)
        return result.scalars().all()


# Global service instance
monitoring_service = PriceMonitoringService()