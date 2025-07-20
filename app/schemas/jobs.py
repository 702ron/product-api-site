"""
Pydantic schemas for job management endpoints.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.queue import JobStatus, JobPriority


class JobResponse(BaseModel):
    """Job status response schema."""
    job_id: str
    job_type: str
    status: JobStatus
    priority: JobPriority
    progress: float = Field(ge=0, le=100, description="Progress percentage (0-100)")
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response for listing user jobs."""
    jobs: List[JobResponse]
    total: int


class JobStatusResponse(BaseModel):
    """Simple job status response."""
    job_id: str
    status: JobStatus
    progress: float
    message: Optional[str] = None


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    total_pending: int
    total_processing: int
    critical_pending: int
    high_pending: int
    normal_pending: int
    low_pending: int
    redis_connected: bool


class CancelJobRequest(BaseModel):
    """Request to cancel a job."""
    reason: Optional[str] = None


class BulkJobRequest(BaseModel):
    """Base schema for bulk job requests."""
    priority: JobPriority = JobPriority.NORMAL
    max_retries: int = Field(default=3, ge=0, le=10)


class BulkProductJobRequest(BulkJobRequest):
    """Request schema for bulk product jobs."""
    asins: List[str] = Field(min_items=1, max_items=1000)
    marketplace: str = "US"
    
    class Config:
        schema_extra = {
            "example": {
                "asins": ["B08N5WRWNW", "B07YTJ7QTJ", "B08XYZ123"],
                "marketplace": "US",
                "priority": "normal",
                "max_retries": 3
            }
        }


class BulkConversionJobRequest(BulkJobRequest):
    """Request schema for bulk conversion jobs."""
    fnskus: List[str] = Field(min_items=1, max_items=1000)
    
    class Config:
        schema_extra = {
            "example": {
                "fnskus": ["X001ABC123", "X002DEF456", "X003GHI789"],
                "priority": "normal",
                "max_retries": 3
            }
        }


class JobSubmissionResponse(BaseModel):
    """Response when submitting a job."""
    job_id: str
    message: str
    estimated_processing_time_minutes: Optional[int] = None
    status_url: str
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Job submitted successfully",
                "estimated_processing_time_minutes": 5,
                "status_url": "/api/v1/jobs/status/550e8400-e29b-41d4-a716-446655440000"
            }
        }