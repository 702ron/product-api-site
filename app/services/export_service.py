"""
Data export service for admin dashboard functionality.
"""
import csv
import json
import uuid
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.models import (
    AdminAction,
    CreditTransaction,
    QueryLog,
    SecurityEvent,
    User,
)
from app.schemas.admin import ExportJobCreateRequest, ExportJobResponse


class ExportService:
    """Service for handling data exports."""

    def __init__(self):
        self.supported_formats = ["csv", "json", "xlsx"]
        self.supported_export_types = [
            "users",
            "transactions",
            "queries",
            "audit_logs",
            "security_events",
        ]

    async def create_export_job(
        self,
        request: ExportJobCreateRequest,
        admin_user_id: str,
        db: AsyncSession,
    ) -> ExportJobResponse:
        """
        Create a new data export job.

        Args:
            request: Export job request parameters
            admin_user_id: Admin user creating the export
            db: Database session

        Returns:
            ExportJobResponse with job details

        Raises:
            ValidationError: If export parameters are invalid
        """
        # Validate export type and format
        if request.export_type not in self.supported_export_types:
            raise ValidationError(
                f"Unsupported export type: {request.export_type}. "
                f"Supported types: {', '.join(self.supported_export_types)}"
            )

        if request.format not in self.supported_formats:
            raise ValidationError(
                f"Unsupported format: {request.format}. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )

        # Create export job record (simplified - would typically use a background task queue)
        job_id = str(uuid.uuid4())

        # For demonstration, we'll generate the export immediately
        # In production, this would be queued as a background job
        try:
            export_data = await self._generate_export_data(request, db)
            file_content = self._format_export_data(export_data, request.format)
            file_size = len(file_content.encode("utf-8"))

            # In production, upload to cloud storage and get URL
            file_url = f"/api/v1/admin/exports/{job_id}/download"

            # Store file content temporarily (in production, save to cloud storage)
            # This is a simplified implementation

            return ExportJobResponse(
                id=job_id,
                export_type=request.export_type,
                status="completed",
                format=request.format,
                parameters=request.parameters,
                file_url=file_url,
                file_size_bytes=file_size,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7),  # 7 day expiry
                error_message=None,
            )

        except Exception as e:
            return ExportJobResponse(
                id=job_id,
                export_type=request.export_type,
                status="failed",
                format=request.format,
                parameters=request.parameters,
                file_url=None,
                file_size_bytes=None,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                expires_at=None,
                error_message=str(e),
            )

    async def _generate_export_data(
        self, request: ExportJobCreateRequest, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """
        Generate export data based on request parameters.

        Args:
            request: Export job request
            db: Database session

        Returns:
            List of dictionaries containing export data
        """
        # Build date filter conditions
        conditions = []
        if request.start_date:
            conditions.append(
                self._get_created_at_column(request.export_type) >= request.start_date
            )
        if request.end_date:
            conditions.append(
                self._get_created_at_column(request.export_type) <= request.end_date
            )

        if request.export_type == "users":
            return await self._export_users(conditions, request.filters, db)
        elif request.export_type == "transactions":
            return await self._export_transactions(conditions, request.filters, db)
        elif request.export_type == "queries":
            return await self._export_queries(conditions, request.filters, db)
        elif request.export_type == "audit_logs":
            return await self._export_audit_logs(conditions, request.filters, db)
        elif request.export_type == "security_events":
            return await self._export_security_events(conditions, request.filters, db)
        else:
            raise ValidationError(f"Unknown export type: {request.export_type}")

    def _get_created_at_column(self, export_type: str):
        """Get the created_at column for the given export type."""
        column_map = {
            "users": User.created_at,
            "transactions": CreditTransaction.created_at,
            "queries": QueryLog.created_at,
            "audit_logs": AdminAction.created_at,
            "security_events": SecurityEvent.created_at,
        }
        return column_map.get(export_type)

    async def _export_users(
        self, conditions: list, filters: dict, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Export user data."""
        query = select(User)

        # Apply date conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply filters
        if filters.get("is_active") is not None:
            query = query.where(User.is_active == filters["is_active"])
        if filters.get("is_verified") is not None:
            query = query.where(User.is_verified == filters["is_verified"])

        result = await db.execute(query)
        users = result.scalars().all()

        return [
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "credit_balance": user.credit_balance,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }
            for user in users
        ]

    async def _export_transactions(
        self, conditions: list, filters: dict, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Export transaction data."""
        query = select(CreditTransaction)

        # Apply date conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply filters
        if filters.get("transaction_type"):
            query = query.where(
                CreditTransaction.transaction_type == filters["transaction_type"]
            )
        if filters.get("user_id"):
            query = query.where(CreditTransaction.user_id == filters["user_id"])

        result = await db.execute(query)
        transactions = result.scalars().all()

        return [
            {
                "id": transaction.id,
                "user_id": transaction.user_id,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type,
                "operation": transaction.operation,
                "description": transaction.description,
                "stripe_session_id": transaction.stripe_session_id,
                "stripe_payment_intent_id": transaction.stripe_payment_intent_id,
                "extra_data": transaction.extra_data,
                "created_at": transaction.created_at.isoformat(),
            }
            for transaction in transactions
        ]

    async def _export_queries(
        self, conditions: list, filters: dict, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Export query log data."""
        query = select(QueryLog)

        # Apply date conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply filters
        if filters.get("query_type"):
            query = query.where(QueryLog.query_type == filters["query_type"])
        if filters.get("status"):
            query = query.where(QueryLog.status == filters["status"])
        if filters.get("user_id"):
            query = query.where(QueryLog.user_id == filters["user_id"])

        result = await db.execute(query)
        queries = result.scalars().all()

        return [
            {
                "id": query.id,
                "user_id": query.user_id,
                "query_type": query.query_type,
                "query_input": query.query_input,
                "credits_deducted": query.credits_deducted,
                "status": query.status,
                "response_time_ms": query.response_time_ms,
                "api_response_summary": query.api_response_summary,
                "error_details": query.error_details,
                "ip_address": query.ip_address,
                "user_agent": query.user_agent,
                "endpoint": query.endpoint,
                "created_at": query.created_at.isoformat(),
            }
            for query in queries
        ]

    async def _export_audit_logs(
        self, conditions: list, filters: dict, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Export audit log data."""
        query = select(AdminAction)

        # Apply date conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply filters
        if filters.get("action_type"):
            query = query.where(AdminAction.action_type == filters["action_type"])
        if filters.get("resource_type"):
            query = query.where(AdminAction.resource_type == filters["resource_type"])
        if filters.get("admin_user_id"):
            query = query.where(AdminAction.admin_user_id == filters["admin_user_id"])
        if filters.get("success") is not None:
            query = query.where(AdminAction.success == filters["success"])

        result = await db.execute(query)
        actions = result.scalars().all()

        return [
            {
                "id": action.id,
                "admin_user_id": action.admin_user_id,
                "action_type": action.action_type,
                "resource_type": action.resource_type,
                "resource_id": action.resource_id,
                "details": action.details,
                "ip_address": action.ip_address,
                "user_agent": action.user_agent,
                "success": action.success,
                "error_message": action.error_message,
                "duration_ms": action.duration_ms,
                "created_at": action.created_at.isoformat(),
            }
            for action in actions
        ]

    async def _export_security_events(
        self, conditions: list, filters: dict, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Export security event data."""
        query = select(SecurityEvent)

        # Apply date conditions
        if conditions:
            query = query.where(and_(*conditions))

        # Apply filters
        if filters.get("event_type"):
            query = query.where(SecurityEvent.event_type == filters["event_type"])
        if filters.get("severity"):
            query = query.where(SecurityEvent.severity == filters["severity"])
        if filters.get("resolved") is not None:
            query = query.where(SecurityEvent.resolved == filters["resolved"])
        if filters.get("user_id"):
            query = query.where(SecurityEvent.user_id == filters["user_id"])

        result = await db.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "user_id": event.user_id,
                "admin_user_id": event.admin_user_id,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "details": event.details,
                "resolved": event.resolved,
                "resolved_by": event.resolved_by,
                "resolved_at": event.resolved_at.isoformat()
                if event.resolved_at
                else None,
                "source": event.source,
                "risk_score": event.risk_score,
                "false_positive": event.false_positive,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]

    def _format_export_data(
        self, data: list[dict[str, Any]], format_type: str
    ) -> str:
        """
        Format export data in the requested format.

        Args:
            data: List of dictionaries containing data to export
            format_type: Output format (csv, json, xlsx)

        Returns:
            Formatted data as string
        """
        if format_type == "json":
            return json.dumps(data, indent=2, default=str)

        elif format_type == "csv":
            if not data:
                return ""

            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        elif format_type == "xlsx":
            # For XLSX format, you would typically use a library like openpyxl
            # For simplicity, we'll return CSV format with a note
            # In production, implement proper XLSX generation
            csv_data = self._format_export_data(data, "csv")
            return f"# XLSX format requested but returning CSV for demo\n{csv_data}"

        else:
            raise ValidationError(f"Unsupported format: {format_type}")

    async def get_export_job(
        self, job_id: str, admin_user_id: str, db: AsyncSession
    ) -> Optional[ExportJobResponse]:
        """
        Get export job details.

        Args:
            job_id: Export job ID
            admin_user_id: Admin user requesting the job
            db: Database session

        Returns:
            ExportJobResponse or None if not found
        """
        # In production, this would query an export_jobs table
        # For demo purposes, return a mock response
        return ExportJobResponse(
            id=job_id,
            export_type="users",
            status="completed",
            format="csv",
            parameters={},
            file_url=f"/api/v1/admin/exports/{job_id}/download",
            file_size_bytes=1024,
            created_at=datetime.utcnow() - timedelta(minutes=5),
            completed_at=datetime.utcnow() - timedelta(minutes=3),
            expires_at=datetime.utcnow() + timedelta(days=7),
            error_message=None,
        )

    async def download_export_file(
        self, job_id: str, admin_user_id: str, db: AsyncSession
    ) -> tuple[str, str]:
        """
        Download export file content.

        Args:
            job_id: Export job ID
            admin_user_id: Admin user requesting download
            db: Database session

        Returns:
            Tuple of (file_content, mime_type)

        Raises:
            ValidationError: If job not found or access denied
        """
        # In production, retrieve file from cloud storage
        # For demo, return sample data
        job = await self.get_export_job(job_id, admin_user_id, db)

        if not job:
            raise ValidationError("Export job not found")

        if job.status != "completed":
            raise ValidationError(f"Export job status is {job.status}, not completed")

        if job.expires_at and job.expires_at < datetime.utcnow():
            raise ValidationError("Export file has expired")

        # Generate sample content based on format
        sample_data = [
            {
                "id": "sample-id-1",
                "email": "user1@example.com",
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "id": "sample-id-2",
                "email": "user2@example.com",
                "created_at": datetime.utcnow().isoformat(),
            },
        ]

        content = self._format_export_data(sample_data, job.format)
        mime_type = self._get_mime_type(job.format)

        return content, mime_type

    def _get_mime_type(self, format_type: str) -> str:
        """Get MIME type for format."""
        mime_types = {
            "csv": "text/csv",
            "json": "application/json",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        return mime_types.get(format_type, "text/plain")

    async def cleanup_expired_exports(self, db: AsyncSession) -> int:
        """
        Clean up expired export files.

        Args:
            db: Database session

        Returns:
            Number of cleaned up files
        """
        # In production, this would:
        # 1. Query export_jobs table for expired files
        # 2. Delete files from cloud storage
        # 3. Update database records
        # 4. Return count of cleaned files

        # For demo purposes, return 0
        return 0

    def validate_export_request(self, request: ExportJobCreateRequest) -> None:
        """
        Validate export request parameters.

        Args:
            request: Export request to validate

        Raises:
            ValidationError: If request is invalid
        """
        # Validate date range
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                raise ValidationError("Start date must be before end date")

            # Limit date range to prevent huge exports
            max_days = 365
            if (request.end_date - request.start_date).days > max_days:
                raise ValidationError(
                    f"Date range cannot exceed {max_days} days"
                )

        # Validate export-specific filters
        if request.export_type == "transactions":
            valid_transaction_types = ["purchase", "usage", "refund", "adjustment"]
            if (
                request.filters.get("transaction_type")
                and request.filters["transaction_type"] not in valid_transaction_types
            ):
                raise ValidationError(
                    f"Invalid transaction_type. Valid types: {valid_transaction_types}"
                )

        elif request.export_type == "queries":
            valid_query_types = ["asin_query", "fnsku_conversion", "bulk_query"]
            if (
                request.filters.get("query_type")
                and request.filters["query_type"] not in valid_query_types
            ):
                raise ValidationError(
                    f"Invalid query_type. Valid types: {valid_query_types}"
                )

        elif request.export_type == "security_events":
            valid_severities = ["low", "medium", "high", "critical"]
            if (
                request.filters.get("severity")
                and request.filters["severity"] not in valid_severities
            ):
                raise ValidationError(
                    f"Invalid severity. Valid severities: {valid_severities}"
                )
