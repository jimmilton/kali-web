"""Tool execution service.

Copyright 2025 milbert.ai

Handles tool execution using local runner and embedded task queue.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.db.session import async_session
from app.models.job import Job, JobOutput, JobStatus
from app.services.tool_runner import ToolRunner
from app.services.task_queue import enqueue_task
from app.tools.registry import get_tool

logger = logging.getLogger(__name__)


async def execute_tool_async(job_id: str) -> dict:
    """
    Execute a tool for a job.

    Args:
        job_id: The job ID to execute

    Returns:
        Dict with execution result
    """
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

        # Emit status update via WebSocket
        await _emit_status(job_id, "running")

        # Initialize local tool runner
        runner = ToolRunner(
            command=job.command,
            timeout=job.timeout_seconds or settings.tool_timeout_default,
            working_dir=str(settings.outputs_path / job_id),
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
            await _emit_output(job_id, output, output_type)

        try:
            # Run the tool
            exit_code, process_id = await runner.run(output_callback)

            job.exit_code = exit_code
            job.completed_at = datetime.utcnow()

            if exit_code == 0:
                job.status = JobStatus.COMPLETED.value
            else:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Tool exited with code {exit_code}"

            await db.commit()

            # Emit completion status
            await _emit_status(job_id, job.status, {"exit_code": exit_code})

            # Parse results if successful
            if exit_code == 0 and tool.output.parser:
                try:
                    enqueue_task(
                        parse_job_results_async,
                        job_id,
                        task_name=f"parse:{job_id}",
                    )
                except Exception as e:
                    logger.error(f"Failed to queue result parsing: {e}")

            return {"success": True, "exit_code": exit_code}

        except asyncio.TimeoutError:
            job.status = JobStatus.FAILED.value
            job.error_message = f"Execution timed out after {job.timeout_seconds} seconds"
            job.completed_at = datetime.utcnow()
            await db.commit()
            await _emit_status(job_id, "timeout")
            return {"error": "timeout"}

        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            job.status = JobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()
            await _emit_status(job_id, "failed", {"error": str(e)})
            return {"error": str(e)}


async def parse_job_results_async(job_id: str) -> dict:
    """Parse job results and create assets/vulnerabilities."""
    from app.tools.parsers import get_parser

    logger.info(f"Parsing results for job {job_id}")

    async with async_session() as db:
        # Get job with outputs
        result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
        job = result.scalar_one_or_none()

        if not job:
            return {"error": "Job not found"}

        # Get tool and parser
        tool = get_tool(job.tool_name)
        if not tool or not tool.output.parser:
            return {"error": "No parser for tool"}

        parser = get_parser(tool.output.parser)
        if not parser:
            return {"error": f"Parser '{tool.output.parser}' not found"}

        # Get all outputs
        outputs_result = await db.execute(
            select(JobOutput)
            .where(JobOutput.job_id == job.id)
            .order_by(JobOutput.sequence)
        )
        outputs = outputs_result.scalars().all()

        # Concatenate stdout
        stdout = "\n".join(o.content for o in outputs if o.output_type == "stdout")

        # Parse
        try:
            parse_result = await parser.parse(stdout, job, db)
            await db.commit()

            logger.info(
                f"Parsed job {job_id}: "
                f"{len(parse_result.assets)} assets, "
                f"{len(parse_result.vulnerabilities)} vulns"
            )

            return {
                "success": True,
                "assets": len(parse_result.assets),
                "vulnerabilities": len(parse_result.vulnerabilities),
            }

        except Exception as e:
            logger.exception(f"Parsing failed: {e}")
            return {"error": str(e)}


async def cancel_job_async(job_id: str) -> dict:
    """Cancel a running job."""
    async with async_session() as db:
        result = await db.execute(select(Job).where(Job.id == UUID(job_id)))
        job = result.scalar_one_or_none()

        if not job:
            return {"error": "Job not found"}

        if job.status != JobStatus.RUNNING.value:
            return {"error": "Job is not running"}

        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.utcnow()
        await db.commit()

        await _emit_status(job_id, "cancelled")
        return {"success": True}


def execute_tool(job_id: str) -> dict:
    """Synchronous wrapper for tool execution."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(execute_tool_async(job_id))
    finally:
        loop.close()


async def _emit_status(job_id: str, status: str, data: Optional[dict] = None):
    """Emit job status via WebSocket."""
    try:
        from app.websocket.manager import emit_job_status
        await emit_job_status(job_id, status, data)
    except Exception as e:
        logger.warning(f"Failed to emit status: {e}")


async def _emit_output(job_id: str, content: str, output_type: str):
    """Emit job output via WebSocket."""
    try:
        from app.websocket.manager import emit_job_output
        await emit_job_output(job_id, content, output_type)
    except Exception as e:
        logger.warning(f"Failed to emit output: {e}")
