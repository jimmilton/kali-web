"""Tool execution tasks."""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.db.session import async_session
from app.models.job import Job, JobOutput, JobStatus
from app.tools.registry import get_tool
from worker.docker_runner import DockerRunner

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def execute_tool(self, job_id: str):
    """Execute a tool in a Docker container."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_execute_tool_async(self, job_id))


async def _execute_tool_async(task, job_id: str):
    """Async implementation of tool execution."""
    logger.info(f"Starting tool execution for job {job_id}")

    async with async_session() as db:
        # Get job
        result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"Job {job_id} not found")
            return {"error": "Job not found"}

        # Get tool definition
        tool = get_tool(job.tool_name)
        if not tool:
            job.status = JobStatus.FAILED.value
            job.error_message = f"Tool '{job.tool_name}' not found"
            job.completed_at = datetime.utcnow()
            await db.commit()
            return {"error": "Tool not found"}

        # Update job status to running
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        await db.commit()

        # Emit status update
        try:
            from app.websocket.manager import emit_job_status
            await emit_job_status(job_id, "running")
        except Exception as e:
            logger.warning(f"Failed to emit status: {e}")

        # Initialize Docker runner
        runner = DockerRunner(
            image=tool.docker_image,
            command=job.command,
            timeout=job.timeout_seconds,
            memory_limit=tool.memory_limit,
            cpu_limit=tool.cpu_limit,
            network_mode=tool.network_mode,
        )

        sequence = 0

        async def output_callback(output: str, output_type: str):
            """Callback to handle command output."""
            nonlocal sequence

            # Store output in database
            output_record = JobOutput(
                job_id=job.id,
                sequence=sequence,
                output_type=output_type,
                content=output,
                timestamp=datetime.utcnow(),
            )
            db.add(output_record)
            await db.flush()
            sequence += 1

            # Emit to WebSocket
            try:
                from app.websocket.manager import emit_job_output
                await emit_job_output(job_id, output, output_type)
            except Exception as e:
                logger.warning(f"Failed to emit output: {e}")

        try:
            # Run the tool
            exit_code, container_id = await runner.run(output_callback)

            job.container_id = container_id
            job.exit_code = exit_code
            job.completed_at = datetime.utcnow()

            if exit_code == 0:
                job.status = JobStatus.COMPLETED.value
            else:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Tool exited with code {exit_code}"

            await db.commit()

            # Emit completion status
            try:
                from app.websocket.manager import emit_job_status
                await emit_job_status(
                    job_id,
                    job.status,
                    {"exit_code": exit_code},
                )
            except Exception as e:
                logger.warning(f"Failed to emit status: {e}")

            # Parse results if successful
            if exit_code == 0 and tool.output.parser:
                try:
                    from worker.tasks.parse_results import parse_job_results
                    parse_job_results.delay(job_id)
                except Exception as e:
                    logger.error(f"Failed to queue result parsing: {e}")

            return {"success": True, "exit_code": exit_code}

        except asyncio.TimeoutError:
            job.status = JobStatus.TIMEOUT.value
            job.error_message = f"Execution timed out after {job.timeout_seconds} seconds"
            job.completed_at = datetime.utcnow()
            await db.commit()

            try:
                from app.websocket.manager import emit_job_status
                await emit_job_status(job_id, "timeout")
            except Exception:
                pass

            return {"error": "timeout"}

        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()

            try:
                from app.websocket.manager import emit_job_status
                await emit_job_status(job_id, "failed", {"error": str(e)})
            except Exception:
                pass

            return {"error": str(e)}


@shared_task
def cleanup_old_jobs():
    """Clean up old completed jobs and their outputs."""
    logger.info("Running job cleanup task")
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_cleanup_old_jobs_async())


async def _cleanup_old_jobs_async():
    """Async implementation of job cleanup."""
    from datetime import timedelta
    from sqlalchemy import delete

    # Clean up jobs older than 30 days
    retention_days = 30
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    async with async_session() as db:
        # Delete job outputs for old completed/failed/cancelled jobs
        old_jobs_subquery = select(Job.id).where(
            Job.status.in_([
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.CANCELLED.value
            ]),
            Job.created_at < cutoff_date
        )

        # Delete outputs first (foreign key constraint)
        output_result = await db.execute(
            delete(JobOutput).where(JobOutput.job_id.in_(old_jobs_subquery))
        )
        outputs_deleted = output_result.rowcount

        # Delete the jobs
        job_result = await db.execute(
            delete(Job).where(
                Job.status.in_([
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value
                ]),
                Job.created_at < cutoff_date
            )
        )
        jobs_deleted = job_result.rowcount

        await db.commit()

        logger.info(f"Cleanup complete: deleted {jobs_deleted} jobs and {outputs_deleted} outputs")
        return {"jobs_deleted": jobs_deleted, "outputs_deleted": outputs_deleted}


@shared_task
def process_scheduled_jobs():
    """Process scheduled jobs that are due."""
    logger.info("Processing scheduled jobs")
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_process_scheduled_jobs_async())


async def _process_scheduled_jobs_async():
    """Async implementation of scheduled job processing."""
    async with async_session() as db:
        # Find jobs that are scheduled and due
        now = datetime.utcnow()
        result = await db.execute(
            select(Job).where(
                Job.status == JobStatus.QUEUED.value,
                Job.scheduled_at <= now,
                Job.scheduled_at.isnot(None),
            )
        )
        jobs = result.scalars().all()

        for job in jobs:
            logger.info(f"Executing scheduled job {job.id}")
            execute_tool.delay(str(job.id))

    return {"processed": len(jobs) if jobs else 0}
