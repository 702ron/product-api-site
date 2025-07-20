"""
Security monitoring service for detecting and managing security events.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import SecurityEvent
from app.schemas.admin import SecurityDashboardResponse, SecurityEventResponse


class SecurityMonitoringService:
    """Service for security monitoring and threat detection."""

    def __init__(self):
        self.risk_thresholds = {
            "failed_login_attempts": settings.admin_max_failed_login_attempts,
            "suspicious_ip_threshold": 10,  # Multiple failed logins from same IP
            "rapid_requests_threshold": 100,  # Requests per minute
            "unusual_hours_threshold": 2,  # Logins between 2-6 AM
        }

    async def create_security_event(
        self,
        event_type: str,
        severity: str,
        details: dict[str, Any],
        user_id: Optional[str] = None,
        admin_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        source: str = "system",
        db: AsyncSession = None,
    ) -> SecurityEvent:
        """
        Create a new security event.

        Args:
            event_type: Type of security event
            severity: Event severity (low, medium, high, critical)
            details: Event details and context
            user_id: Optional user ID involved
            admin_user_id: Optional admin user ID involved
            ip_address: Client IP address
            user_agent: Client user agent
            source: Source of the event detection
            db: Database session

        Returns:
            Created SecurityEvent
        """
        # Calculate risk score based on event type and context
        risk_score = self._calculate_risk_score(
            event_type, severity, details, ip_address, user_id, db
        )

        # Create security event
        security_event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            admin_user_id=admin_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            source=source,
            risk_score=await risk_score,
        )

        db.add(security_event)
        await db.commit()
        await db.refresh(security_event)

        # Check if this event should trigger additional monitoring
        await self._check_event_escalation(security_event, db)

        return security_event

    async def _calculate_risk_score(
        self,
        event_type: str,
        severity: str,
        details: dict[str, Any],
        ip_address: Optional[str],
        user_id: Optional[str],
        db: AsyncSession,
    ) -> int:
        """
        Calculate risk score for security event (0-100).

        Args:
            event_type: Type of security event
            severity: Event severity
            details: Event details
            ip_address: Client IP address
            user_id: User ID if applicable
            db: Database session

        Returns:
            Risk score (0-100)
        """
        base_scores = {
            "low": 20,
            "medium": 40,
            "high": 70,
            "critical": 90,
        }

        score = base_scores.get(severity, 50)

        # Event type modifiers
        event_modifiers = {
            "failed_login": 10,
            "suspicious_activity": 15,
            "rate_limit_exceeded": 5,
            "unauthorized_access": 25,
            "data_breach_attempt": 30,
            "admin_privilege_escalation": 35,
            "malicious_request": 20,
            "account_takeover_attempt": 30,
        }

        score += event_modifiers.get(event_type, 0)

        # IP address reputation (simplified)
        if ip_address:
            # Check for recent events from same IP
            recent_events = await self._get_recent_events_by_ip(ip_address, db)
            if recent_events > 5:
                score += min(recent_events * 2, 20)

        # User history (if user involved)
        if user_id:
            user_risk = await self._get_user_risk_factor(user_id, db)
            score += user_risk

        # Time-based factors
        now = datetime.utcnow()
        if 2 <= now.hour <= 6:  # Unusual hours
            score += 5

        # Cap at 100
        return min(score, 100)

    async def _get_recent_events_by_ip(
        self, ip_address: str, db: AsyncSession, hours: int = 24
    ) -> int:
        """Get count of recent security events from IP address."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.ip_address == ip_address,
                    SecurityEvent.created_at >= cutoff,
                )
            )
        )
        return result.scalar() or 0

    async def _get_user_risk_factor(self, user_id: str, db: AsyncSession) -> int:
        """Calculate user risk factor based on history."""
        # Check for recent security events for this user
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.user_id == user_id,
                    SecurityEvent.created_at >= recent_cutoff,
                )
            )
        )
        recent_events = result.scalar() or 0

        # Risk factor: 0-15 points based on recent events
        return min(recent_events * 3, 15)

    async def _check_event_escalation(
        self, event: SecurityEvent, db: AsyncSession
    ) -> None:
        """
        Check if security event should trigger escalation or additional monitoring.

        Args:
            event: Security event to check
            db: Database session
        """
        # Auto-escalate critical events
        if event.severity == "critical" or event.risk_score >= 80:
            await self._escalate_security_event(event, db)

        # Check for patterns that might indicate coordinated attacks
        if event.ip_address:
            await self._check_ip_pattern_escalation(event, db)

        if event.user_id:
            await self._check_user_pattern_escalation(event, db)

    async def _escalate_security_event(
        self, event: SecurityEvent, db: AsyncSession
    ) -> None:
        """
        Escalate high-risk security event.

        Args:
            event: Security event to escalate
            db: Database session
        """
        # In production, this would:
        # 1. Send alerts to security team
        # 2. Trigger automated responses (IP blocking, account suspension)
        # 3. Create incident tickets
        # 4. Update security monitoring rules

        # For now, create a follow-up event
        escalation_details = {
            "original_event_id": event.id,
            "escalation_reason": "High risk score or critical severity",
            "risk_score": event.risk_score,
            "automated_escalation": True,
        }

        await self.create_security_event(
            event_type="security_escalation",
            severity="high",
            details=escalation_details,
            source="automated_escalation",
            db=db,
        )

    async def _check_ip_pattern_escalation(
        self, event: SecurityEvent, db: AsyncSession
    ) -> None:
        """Check for suspicious IP address patterns."""
        if not event.ip_address:
            return

        # Check for multiple failed logins from same IP in short time
        recent_cutoff = datetime.utcnow() - timedelta(minutes=15)
        result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.ip_address == event.ip_address,
                    SecurityEvent.event_type == "failed_login",
                    SecurityEvent.created_at >= recent_cutoff,
                )
            )
        )
        recent_failed_logins = result.scalar() or 0

        if recent_failed_logins >= 5:
            await self.create_security_event(
                event_type="suspicious_ip_activity",
                severity="medium",
                details={
                    "ip_address": event.ip_address,
                    "failed_login_count": recent_failed_logins,
                    "time_window_minutes": 15,
                    "trigger_event_id": event.id,
                },
                ip_address=event.ip_address,
                source="pattern_detection",
                db=db,
            )

    async def _check_user_pattern_escalation(
        self, event: SecurityEvent, db: AsyncSession
    ) -> None:
        """Check for suspicious user behavior patterns."""
        if not event.user_id:
            return

        # Check for multiple security events for same user
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.user_id == event.user_id,
                    SecurityEvent.created_at >= recent_cutoff,
                )
            )
        )
        recent_events = result.scalar() or 0

        if recent_events >= 3:
            await self.create_security_event(
                event_type="suspicious_user_activity",
                severity="medium",
                details={
                    "user_id": event.user_id,
                    "event_count": recent_events,
                    "time_window_hours": 1,
                    "trigger_event_id": event.id,
                },
                user_id=event.user_id,
                source="pattern_detection",
                db=db,
            )

    async def get_security_dashboard(self, db: AsyncSession) -> SecurityDashboardResponse:
        """
        Get security monitoring dashboard data.

        Args:
            db: Database session

        Returns:
            SecurityDashboardResponse with current security metrics
        """
        now = datetime.utcnow()
        twenty_four_hours_ago = now - timedelta(hours=24)

        # Open alerts (unresolved)
        open_alerts_result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.resolved == False
            )
        )
        open_alerts = open_alerts_result.scalar() or 0

        # High severity alerts (unresolved)
        high_severity_result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.resolved == False,
                    SecurityEvent.severity == "high",
                )
            )
        )
        high_severity_alerts = high_severity_result.scalar() or 0

        # Critical alerts (unresolved)
        critical_alerts_result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.resolved == False,
                    SecurityEvent.severity == "critical",
                )
            )
        )
        critical_alerts = critical_alerts_result.scalar() or 0

        # Failed logins in last 24 hours
        failed_logins_result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.event_type == "failed_login",
                    SecurityEvent.created_at >= twenty_four_hours_ago,
                )
            )
        )
        failed_logins_24h = failed_logins_result.scalar() or 0

        # Suspicious activity in last 24 hours
        suspicious_activity_result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    or_(
                        SecurityEvent.event_type == "suspicious_activity",
                        SecurityEvent.event_type == "suspicious_ip_activity",
                        SecurityEvent.event_type == "suspicious_user_activity",
                    ),
                    SecurityEvent.created_at >= twenty_four_hours_ago,
                )
            )
        )
        suspicious_activity_24h = suspicious_activity_result.scalar() or 0

        # Get blocked IPs (IPs with multiple recent failed attempts)
        blocked_ips_result = await db.execute(
            select(SecurityEvent.ip_address, func.count(SecurityEvent.id).label("count"))
            .where(
                and_(
                    SecurityEvent.event_type == "failed_login",
                    SecurityEvent.created_at >= twenty_four_hours_ago,
                    SecurityEvent.ip_address.isnot(None),
                )
            )
            .group_by(SecurityEvent.ip_address)
            .having(func.count(SecurityEvent.id) >= 5)
        )
        blocked_ips = [row.ip_address for row in blocked_ips_result.fetchall()]

        # Calculate overall risk score
        overall_risk_score = await self._calculate_overall_risk_score(db)

        # Get top risks
        top_risks = await self._get_top_security_risks(db)

        return SecurityDashboardResponse(
            timestamp=now,
            open_alerts=open_alerts,
            high_severity_alerts=high_severity_alerts,
            critical_alerts=critical_alerts,
            failed_logins_24h=failed_logins_24h,
            suspicious_activity_24h=suspicious_activity_24h,
            blocked_ips=blocked_ips,
            overall_risk_score=overall_risk_score,
            top_risks=top_risks,
        )

    async def _calculate_overall_risk_score(self, db: AsyncSession) -> int:
        """Calculate overall system risk score."""
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)

        # Get average risk score of recent unresolved events
        result = await db.execute(
            select(func.avg(SecurityEvent.risk_score)).where(
                and_(
                    SecurityEvent.resolved == False,
                    SecurityEvent.created_at >= recent_cutoff,
                )
            )
        )
        avg_risk = result.scalar() or 0

        # Adjust based on volume of events
        volume_result = await db.execute(
            select(func.count(SecurityEvent.id)).where(
                and_(
                    SecurityEvent.resolved == False,
                    SecurityEvent.created_at >= recent_cutoff,
                )
            )
        )
        event_volume = volume_result.scalar() or 0

        # Volume modifier: +1 point per 5 unresolved events
        volume_modifier = min(event_volume // 5, 20)

        return min(int(avg_risk + volume_modifier), 100)

    async def _get_top_security_risks(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Get top security risks by event type and severity."""
        recent_cutoff = datetime.utcnow() - timedelta(days=7)

        result = await db.execute(
            select(
                SecurityEvent.event_type,
                SecurityEvent.severity,
                func.count(SecurityEvent.id).label("count"),
                func.avg(SecurityEvent.risk_score).label("avg_risk"),
            )
            .where(
                and_(
                    SecurityEvent.created_at >= recent_cutoff,
                    SecurityEvent.resolved == False,
                )
            )
            .group_by(SecurityEvent.event_type, SecurityEvent.severity)
            .order_by(desc(func.count(SecurityEvent.id)))
            .limit(5)
        )

        return [
            {
                "event_type": row.event_type,
                "severity": row.severity,
                "count": row.count,
                "average_risk_score": round(row.avg_risk or 0, 1),
                "description": self._get_risk_description(row.event_type),
            }
            for row in result.fetchall()
        ]

    def _get_risk_description(self, event_type: str) -> str:
        """Get human-readable description for event type."""
        descriptions = {
            "failed_login": "Failed authentication attempts",
            "suspicious_activity": "Unusual user behavior patterns",
            "rate_limit_exceeded": "Excessive API requests",
            "unauthorized_access": "Attempted access to restricted resources",
            "suspicious_ip_activity": "Multiple failed attempts from same IP",
            "suspicious_user_activity": "Multiple security events for same user",
            "admin_privilege_escalation": "Attempted privilege escalation",
            "malicious_request": "Potentially malicious API requests",
        }
        return descriptions.get(event_type, "Unknown security event")

    async def resolve_security_event(
        self,
        event_id: int,
        resolved_by: str,
        resolution_notes: Optional[str] = None,
        false_positive: bool = False,
        db: AsyncSession = None,
    ) -> Optional[SecurityEvent]:
        """
        Resolve a security event.

        Args:
            event_id: Security event ID
            resolved_by: Admin user ID resolving the event
            resolution_notes: Optional resolution notes
            false_positive: Whether this was a false positive
            db: Database session

        Returns:
            Updated SecurityEvent or None if not found
        """
        result = await db.execute(
            select(SecurityEvent).where(SecurityEvent.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return None

        event.resolved = True
        event.resolved_by = resolved_by
        event.resolved_at = datetime.utcnow()
        event.false_positive = false_positive

        # Add resolution notes to details
        if resolution_notes:
            if event.details is None:
                event.details = {}
            event.details["resolution_notes"] = resolution_notes
            event.details["resolved_at"] = datetime.utcnow().isoformat()

        await db.commit()
        await db.refresh(event)

        return event

    async def get_security_events(
        self,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None,
    ) -> list[SecurityEventResponse]:
        """
        Get security events with filtering.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            event_type: Filter by event type
            severity: Filter by severity
            resolved: Filter by resolution status
            start_date: Start date filter
            end_date: End date filter
            db: Database session

        Returns:
            List of SecurityEventResponse objects
        """
        query = select(SecurityEvent)

        # Build filter conditions
        conditions = []
        if event_type:
            conditions.append(SecurityEvent.event_type == event_type)
        if severity:
            conditions.append(SecurityEvent.severity == severity)
        if resolved is not None:
            conditions.append(SecurityEvent.resolved == resolved)
        if start_date:
            conditions.append(SecurityEvent.created_at >= start_date)
        if end_date:
            conditions.append(SecurityEvent.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = (
            query.order_by(desc(SecurityEvent.created_at)).offset(skip).limit(limit)
        )

        result = await db.execute(query)
        events = result.scalars().all()

        return [
            SecurityEventResponse(
                id=event.id,
                event_type=event.event_type,
                severity=event.severity,
                user_id=event.user_id,
                admin_user_id=event.admin_user_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                details=event.details,
                resolved=event.resolved,
                resolved_by=event.resolved_by,
                resolved_at=event.resolved_at,
                created_at=event.created_at,
                source=event.source,
                risk_score=event.risk_score,
                false_positive=event.false_positive,
            )
            for event in events
        ]

    async def detect_anomalies(self, db: AsyncSession) -> list[dict[str, Any]]:
        """
        Detect security anomalies using pattern analysis.

        Args:
            db: Database session

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Check for unusual login patterns
        login_anomalies = await self._detect_login_anomalies(db)
        anomalies.extend(login_anomalies)

        # Check for API usage anomalies
        api_anomalies = await self._detect_api_anomalies(db)
        anomalies.extend(api_anomalies)

        # Check for geographic anomalies (if geo data available)
        # geo_anomalies = await self._detect_geographic_anomalies(db)
        # anomalies.extend(geo_anomalies)

        return anomalies

    async def _detect_login_anomalies(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect unusual login patterns."""
        anomalies = []
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)

        # Detect failed login spikes
        result = await db.execute(
            select(
                SecurityEvent.ip_address,
                func.count(SecurityEvent.id).label("failed_count"),
            )
            .where(
                and_(
                    SecurityEvent.event_type == "failed_login",
                    SecurityEvent.created_at >= recent_cutoff,
                    SecurityEvent.ip_address.isnot(None),
                )
            )
            .group_by(SecurityEvent.ip_address)
            .having(func.count(SecurityEvent.id) > 10)
        )

        for row in result.fetchall():
            anomalies.append(
                {
                    "type": "login_spike",
                    "description": f"Unusual number of failed logins from IP {row.ip_address}",
                    "ip_address": row.ip_address,
                    "failed_count": row.failed_count,
                    "severity": "medium" if row.failed_count < 20 else "high",
                }
            )

        return anomalies

    async def _detect_api_anomalies(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect unusual API usage patterns."""
        # This would typically analyze QueryLog table for unusual patterns
        # For now, return empty list as placeholder
        return []
