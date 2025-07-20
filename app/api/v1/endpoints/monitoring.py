"""
Price monitoring endpoints for Amazon Product Intelligence Platform.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.models import User, PriceMonitor, PriceHistory, PriceAlert
from app.services.monitoring_service import monitoring_service
from app.services.amazon_service import amazon_service
from app.schemas.monitoring import (
    PriceMonitorCreate, PriceMonitorUpdate, PriceMonitorResponse,
    PriceMonitorListResponse, PriceHistoryResponse, PriceHistoryListResponse,
    PriceAlertResponse, PriceAlertListResponse, MonitorStatsResponse,
    BulkMonitorRequest, BulkMonitorResponse, MonitorTestRequest, MonitorTestResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/monitors", response_model=PriceMonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_price_monitor(
    monitor_data: PriceMonitorCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new price monitor for a product.
    
    Monitor will check the product price at the specified frequency and send
    alerts when price conditions are met.
    """
    try:
        monitor = await monitoring_service.create_monitor(
            user_id=str(current_user.id),
            asin=monitor_data.asin,
            name=monitor_data.name,
            marketplace=monitor_data.marketplace,
            target_price=monitor_data.target_price,
            threshold_percentage=monitor_data.threshold_percentage,
            monitor_frequency_minutes=monitor_data.monitor_frequency_minutes,
            email_alerts=monitor_data.email_alerts,
            webhook_url=monitor_data.webhook_url,
            alert_conditions=monitor_data.alert_conditions,
            db=db
        )
        
        return PriceMonitorResponse.from_orm(monitor)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating price monitor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create price monitor"
        )


@router.get("/monitors", response_model=PriceMonitorListResponse)
async def list_price_monitors(
    active_only: bool = Query(True, description="Show only active monitors"),
    limit: int = Query(50, ge=1, le=100, description="Number of monitors to return"),
    offset: int = Query(0, ge=0, description="Number of monitors to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all price monitors for the current user.
    """
    try:
        monitors = await monitoring_service.get_user_monitors(
            user_id=str(current_user.id),
            active_only=active_only,
            db=db
        )
        
        # Apply pagination
        total = len(monitors)
        paginated_monitors = monitors[offset:offset + limit]
        
        return PriceMonitorListResponse(
            monitors=[PriceMonitorResponse.from_orm(m) for m in paginated_monitors],
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing price monitors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list price monitors"
        )


@router.get("/monitors/{monitor_id}", response_model=PriceMonitorResponse)
async def get_price_monitor(
    monitor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific price monitor by ID.
    """
    try:
        query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == str(current_user.id)
            )
        )
        result = await db.execute(query)
        monitor = result.scalar_one_or_none()
        
        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price monitor not found"
            )
        
        return PriceMonitorResponse.from_orm(monitor)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price monitor {monitor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get price monitor"
        )


@router.put("/monitors/{monitor_id}", response_model=PriceMonitorResponse)
async def update_price_monitor(
    monitor_id: str,
    monitor_updates: PriceMonitorUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a price monitor.
    """
    try:
        # Convert to dict and remove None values
        updates = monitor_updates.dict(exclude_unset=True)
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )
        
        monitor = await monitoring_service.update_monitor(
            monitor_id=monitor_id,
            user_id=str(current_user.id),
            updates=updates,
            db=db
        )
        
        return PriceMonitorResponse.from_orm(monitor)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating price monitor {monitor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update price monitor"
        )


@router.delete("/monitors/{monitor_id}")
async def delete_price_monitor(
    monitor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a price monitor.
    """
    try:
        success = await monitoring_service.delete_monitor(
            monitor_id=monitor_id,
            user_id=str(current_user.id),
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price monitor not found"
            )
        
        return {"message": "Price monitor deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting price monitor {monitor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete price monitor"
        )


@router.get("/monitors/{monitor_id}/history", response_model=PriceHistoryListResponse)
async def get_price_history(
    monitor_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get price history for a monitor.
    """
    try:
        # Get monitor first to include in response
        query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == str(current_user.id)
            )
        )
        result = await db.execute(query)
        monitor = result.scalar_one_or_none()
        
        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price monitor not found"
            )
        
        # Get price history
        history = await monitoring_service.get_price_history(
            monitor_id=monitor_id,
            user_id=str(current_user.id),
            days=days,
            db=db
        )
        
        return PriceHistoryListResponse(
            history=[PriceHistoryResponse.from_orm(h) for h in history],
            total=len(history),
            monitor=PriceMonitorResponse.from_orm(monitor)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price history for monitor {monitor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get price history"
        )


@router.get("/monitors/{monitor_id}/alerts", response_model=PriceAlertListResponse)
async def get_price_alerts(
    monitor_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get price alerts for a monitor.
    """
    try:
        # Verify user owns the monitor
        monitor_query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == str(current_user.id)
            )
        )
        monitor_result = await db.execute(monitor_query)
        if not monitor_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price monitor not found"
            )
        
        # Get alerts
        query = select(PriceAlert).where(
            PriceAlert.monitor_id == monitor_id
        ).order_by(desc(PriceAlert.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        # Get total count
        count_query = select(func.count(PriceAlert.id)).where(
            PriceAlert.monitor_id == monitor_id
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return PriceAlertListResponse(
            alerts=[PriceAlertResponse.from_orm(a) for a in alerts],
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price alerts for monitor {monitor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get price alerts"
        )


@router.post("/monitors/{monitor_id}/check")
async def check_monitor_price(
    monitor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a price check for a monitor.
    """
    try:
        # Get monitor
        query = select(PriceMonitor).where(
            and_(
                PriceMonitor.id == monitor_id,
                PriceMonitor.user_id == str(current_user.id),
                PriceMonitor.is_active == True
            )
        )
        result = await db.execute(query)
        monitor = result.scalar_one_or_none()
        
        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active price monitor not found"
            )
        
        # Check price
        await monitoring_service._check_price_for_monitor(monitor, db)
        await db.commit()
        
        return {
            "message": "Price check completed",
            "monitor_id": monitor_id,
            "last_checked_at": monitor.last_checked_at.isoformat(),
            "last_price": monitor.last_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking price for monitor {monitor_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check monitor price"
        )


@router.post("/test", response_model=MonitorTestResponse)
async def test_monitor(
    test_data: MonitorTestRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test price monitoring for a product without creating a monitor.
    """
    try:
        start_time = datetime.utcnow()
        
        # Get product data
        product_data = await amazon_service.get_product_data(
            asin=test_data.asin,
            marketplace=test_data.marketplace,
            user_id=str(current_user.id),
            db=db,
            skip_credit_check=True  # Test doesn't use credits
        )
        
        # Extract price and availability
        price = None
        if hasattr(product_data, 'price') and product_data.price:
            price = float(product_data.price)
        
        availability = None
        if hasattr(product_data, 'availability'):
            availability = product_data.availability
        
        title = None
        if hasattr(product_data, 'title'):
            title = product_data.title
        
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return MonitorTestResponse(
            asin=test_data.asin,
            marketplace=test_data.marketplace,
            current_price=price,
            availability=availability,
            title=title,
            response_time_ms=response_time,
            success=True,
            error_message=None
        )
        
    except Exception as e:
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return MonitorTestResponse(
            asin=test_data.asin,
            marketplace=test_data.marketplace,
            current_price=None,
            availability=None,
            title=None,
            response_time_ms=response_time,
            success=False,
            error_message=str(e)
        )


@router.get("/stats", response_model=MonitorStatsResponse)
async def get_monitor_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get price monitoring statistics for the current user.
    """
    try:
        user_id = str(current_user.id)
        
        # Total monitors
        total_query = select(func.count(PriceMonitor.id)).where(
            PriceMonitor.user_id == user_id
        )
        total_result = await db.execute(total_query)
        total_monitors = total_result.scalar()
        
        # Active monitors
        active_query = select(func.count(PriceMonitor.id)).where(
            and_(
                PriceMonitor.user_id == user_id,
                PriceMonitor.is_active == True
            )
        )
        active_result = await db.execute(active_query)
        active_monitors = active_result.scalar()
        
        # Today's stats
        today = datetime.utcnow().date()
        
        # Checks today
        checks_query = select(func.count(PriceHistory.id)).join(PriceMonitor).where(
            and_(
                PriceMonitor.user_id == user_id,
                func.date(PriceHistory.recorded_at) == today
            )
        )
        checks_result = await db.execute(checks_query)
        total_checks_today = checks_result.scalar()
        
        # Alerts today
        alerts_query = select(func.count(PriceAlert.id)).join(PriceMonitor).where(
            and_(
                PriceMonitor.user_id == user_id,
                func.date(PriceAlert.created_at) == today
            )
        )
        alerts_result = await db.execute(alerts_query)
        total_alerts_today = alerts_result.scalar()
        
        # Average price change (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        avg_change_query = select(func.avg(PriceHistory.price_change_percentage)).join(PriceMonitor).where(
            and_(
                PriceMonitor.user_id == user_id,
                PriceHistory.recorded_at >= week_ago,
                PriceHistory.price_change_percentage.isnot(None)
            )
        )
        avg_change_result = await db.execute(avg_change_query)
        avg_price_change = avg_change_result.scalar() or 0.0
        
        # Top monitored ASINs
        top_asins_query = select(
            PriceMonitor.asin,
            PriceMonitor.name,
            func.count(PriceHistory.id).label('check_count')
        ).join(PriceHistory).where(
            PriceMonitor.user_id == user_id
        ).group_by(PriceMonitor.asin, PriceMonitor.name).order_by(
            desc('check_count')
        ).limit(5)
        
        top_asins_result = await db.execute(top_asins_query)
        top_asins = [
            {"asin": row.asin, "name": row.name, "check_count": row.check_count}
            for row in top_asins_result
        ]
        
        return MonitorStatsResponse(
            total_monitors=total_monitors,
            active_monitors=active_monitors,
            total_checks_today=total_checks_today,
            total_alerts_today=total_alerts_today,
            avg_price_change_percentage=round(avg_price_change, 2),
            top_monitored_asins=top_asins
        )
        
    except Exception as e:
        logger.error(f"Error getting monitor stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get monitor statistics"
        )


@router.get("/analytics")
async def get_analytics(
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    # Temporarily bypass auth for testing
    # current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics data for the current user.
    """
    try:
        from datetime import datetime, timedelta
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow().date().isoformat()
        if not start_date:
            start_date = (datetime.utcnow().date() - timedelta(days=30)).isoformat()
        
        # Mock analytics data for now (replace with real implementation)
        user_stats = {
            "total_api_calls": 150,
            "total_credits_used": 75,
            "total_credits_purchased": 100,
            "average_daily_usage": 2.5,
            "most_used_endpoint": "/api/v1/products/asin",
            "account_age_days": 30
        }
        
        usage_trends = [
            {
                "date": (datetime.utcnow().date() - timedelta(days=i)).isoformat(),
                "api_calls": max(0, 10 - i + (i % 3)),
                "credits_used": max(0, 5 - i//2 + (i % 2)),
                "unique_asins": max(0, 3 - i//5 + (i % 4))
            }
            for i in range(30)
        ]
        
        endpoint_usage = [
            {
                "endpoint": "/api/v1/products/asin",
                "calls": 85,
                "credits_used": 42,
                "average_response_time": 320
            },
            {
                "endpoint": "/api/v1/conversion/fnsku",
                "calls": 35,
                "credits_used": 18,
                "average_response_time": 180
            },
            {
                "endpoint": "/api/v1/monitoring/monitors",
                "calls": 25,
                "credits_used": 12,
                "average_response_time": 150
            },
            {
                "endpoint": "/api/v1/products/bulk",
                "calls": 5,
                "credits_used": 3,
                "average_response_time": 850
            }
        ]
        
        credit_history = [
            {
                "date": (datetime.utcnow().date() - timedelta(days=i*3)).isoformat(),
                "transaction_type": "purchase" if i % 4 == 0 else "usage",
                "amount": 100 if i % 4 == 0 else -(2+i%3),
                "description": f"Credit purchase - Starter Package" if i % 4 == 0 else f"API usage - Product lookup",
                "balance_after": max(0, 100 - (i*2))
            }
            for i in range(10)
        ]
        
        marketplace_breakdown = [
            {"marketplace": "US", "calls": 95, "percentage": 63.3},
            {"marketplace": "GB", "calls": 25, "percentage": 16.7},
            {"marketplace": "DE", "calls": 15, "percentage": 10.0},
            {"marketplace": "CA", "calls": 10, "percentage": 6.7},
            {"marketplace": "FR", "calls": 5, "percentage": 3.3}
        ]
        
        return {
            "user_stats": user_stats,
            "usage_trends": usage_trends,
            "endpoint_usage": endpoint_usage,
            "credit_history": credit_history,
            "marketplace_breakdown": marketplace_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics data"
        )


@router.post("/bulk", response_model=BulkMonitorResponse)
async def bulk_monitor_action(
    bulk_request: BulkMonitorRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform bulk actions on multiple monitors.
    """
    try:
        results = []
        success_count = 0
        failure_count = 0
        
        for monitor_id in bulk_request.monitor_ids:
            try:
                # Get monitor
                query = select(PriceMonitor).where(
                    and_(
                        PriceMonitor.id == monitor_id,
                        PriceMonitor.user_id == str(current_user.id)
                    )
                )
                result = await db.execute(query)
                monitor = result.scalar_one_or_none()
                
                if not monitor:
                    results.append({
                        "monitor_id": monitor_id,
                        "success": False,
                        "error": "Monitor not found"
                    })
                    failure_count += 1
                    continue
                
                # Perform action
                if bulk_request.action == "activate":
                    monitor.is_active = True
                elif bulk_request.action == "deactivate":
                    monitor.is_active = False
                elif bulk_request.action == "delete":
                    monitor.is_active = False
                
                monitor.updated_at = datetime.utcnow()
                
                results.append({
                    "monitor_id": monitor_id,
                    "success": True,
                    "action": bulk_request.action
                })
                success_count += 1
                
            except Exception as e:
                results.append({
                    "monitor_id": monitor_id,
                    "success": False,
                    "error": str(e)
                })
                failure_count += 1
        
        await db.commit()
        
        return BulkMonitorResponse(
            success_count=success_count,
            failure_count=failure_count,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error performing bulk monitor action: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk action"
        )