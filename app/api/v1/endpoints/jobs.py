"""
Job management endpoints for queue system.
Provides job status tracking, progress monitoring, and result retrieval.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.queue import get_queue, JobStatus, JobPriority
from app.models.models import User
from app.schemas.jobs import (
    JobResponse, JobListResponse, JobStatusResponse, 
    QueueStatsResponse, CancelJobRequest
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get job status and details.
    """
    try:
        queue = await get_queue()
        job_data = await queue.get_job(job_id)
        
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Verify user owns this job
        if job_data.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        return JobResponse(
            job_id=job_data.job_id,
            job_type=job_data.job_type,
            status=job_data.status,
            priority=job_data.priority,
            progress=job_data.progress,
            created_at=job_data.created_at,
            started_at=job_data.started_at,
            completed_at=job_data.completed_at,
            result=job_data.result,
            error=job_data.error,
            retry_count=job_data.retry_count,
            max_retries=job_data.max_retries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status"
        )


@router.get("/my-jobs", response_model=JobListResponse)
async def get_user_jobs(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all jobs for the current user.
    """
    try:
        queue = await get_queue()
        jobs = await queue.get_user_jobs(str(current_user.id), limit=limit)
        
        job_responses = []
        for job_data in jobs:
            job_responses.append(JobResponse(
                job_id=job_data.job_id,
                job_type=job_data.job_type,
                status=job_data.status,
                priority=job_data.priority,
                progress=job_data.progress,
                created_at=job_data.created_at,
                started_at=job_data.started_at,
                completed_at=job_data.completed_at,
                result=job_data.result,
                error=job_data.error,
                retry_count=job_data.retry_count,
                max_retries=job_data.max_retries
            ))
        
        return JobListResponse(
            jobs=job_responses,
            total=len(job_responses)
        )
        
    except Exception as e:
        logger.error(f"Error getting user jobs for {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user jobs"
        )


@router.post("/cancel/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a pending or processing job.
    """
    try:
        queue = await get_queue()
        job_data = await queue.get_job(job_id)
        
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Verify user owns this job
        if job_data.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        # Check if job can be cancelled
        if job_data.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job_data.status}"
            )
        
        await queue.cancel_job(job_id)
        
        return {"message": "Job cancelled successfully", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )


@router.get("/queue-stats", response_model=QueueStatsResponse)
async def get_queue_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get queue statistics (for monitoring).
    """
    try:
        queue = await get_queue()
        stats = await queue.get_queue_stats()
        
        return QueueStatsResponse(
            total_pending=stats["total_pending"],
            total_processing=stats["total_processing"],
            critical_pending=stats.get("critical_pending", 0),
            high_pending=stats.get("high_pending", 0),
            normal_pending=stats.get("normal_pending", 0),
            low_pending=stats.get("low_pending", 0),
            redis_connected=stats["redis_connected"]
        )
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue statistics"
        )