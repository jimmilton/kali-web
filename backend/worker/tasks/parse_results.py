"""Result parsing tasks for processing tool output."""

import asyncio
import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import async_session
from app.models.job import Job, JobOutput
from app.tools.parsers import get_parser
from app.tools.registry import get_tool

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def parse_job_results(self, job_id: str) -> dict:
    """
    Parse results from a completed job.

    This task is queued after a tool execution completes successfully.
    It retrieves the job output, parses it using the appropriate parser,
    and creates Assets, Vulnerabilities, Credentials, and Results.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_parse_job_results_async(self, job_id))


async def _parse_job_results_async(task, job_id: str):
    """Async implementation of result parsing."""
    logger.info(f"Starting result parsing for job {job_id}")

    async with async_session() as db:
        # Get job with outputs
        result = await db.execute(
            select(Job)
            .where(Job.id == UUID(job_id))
            .options(selectinload(Job.outputs))
        )
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"Job {job_id} not found")
            return {"error": "Job not found"}

        # Get tool definition to find parser name
        tool = get_tool(job.tool_name)
        if not tool:
            logger.error(f"Tool '{job.tool_name}' not found in registry")
            return {"error": "Tool not found"}

        if not tool.output.parser:
            logger.info(f"No parser configured for tool '{job.tool_name}'")
            return {"skipped": "No parser configured"}

        # Get parser instance
        parser = get_parser(tool.output.parser)
        if not parser:
            logger.error(f"Parser '{tool.output.parser}' not found")
            return {"error": "Parser not found"}

        # Get job outputs ordered by sequence
        output_result = await db.execute(
            select(JobOutput)
            .where(JobOutput.job_id == job.id)
            .where(JobOutput.output_type == "stdout")
            .order_by(JobOutput.sequence)
        )
        outputs = output_result.scalars().all()

        if not outputs:
            logger.warning(f"No output found for job {job_id}")
            return {"skipped": "No output to parse"}

        # Concatenate all stdout chunks
        raw_output = "".join(output.content for output in outputs)

        if not raw_output.strip():
            logger.warning(f"Empty output for job {job_id}")
            return {"skipped": "Empty output"}

        try:
            # Parse the output
            logger.info(f"Parsing {len(raw_output)} bytes with {tool.output.parser}")
            parse_output = parser.parse(raw_output, job)

            # Log any parsing errors
            for error in parse_output.errors:
                logger.warning(f"Parse error: {error}")

            # Save results to database
            stats = await parser.save_results(db, job, parse_output)

            logger.info(
                f"Parsing complete for job {job_id}: "
                f"assets={stats['assets_created']}+{stats['assets_updated']}, "
                f"vulns={stats['vulnerabilities_created']}+{stats['vulnerabilities_updated']}, "
                f"creds={stats['credentials_created']}+{stats['credentials_updated']}, "
                f"results={stats['results_created']}"
            )

            # Emit WebSocket notification
            try:
                from app.websocket.manager import emit_job_status
                await emit_job_status(
                    job_id,
                    "parsed",
                    {
                        "assets_created": stats["assets_created"],
                        "assets_updated": stats["assets_updated"],
                        "vulnerabilities_created": stats["vulnerabilities_created"],
                        "vulnerabilities_updated": stats["vulnerabilities_updated"],
                        "credentials_created": stats["credentials_created"],
                        "credentials_updated": stats["credentials_updated"],
                        "results_created": stats["results_created"],
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to emit parse status: {e}")

            return {"success": True, "stats": stats}

        except Exception as e:
            logger.exception(f"Failed to parse results for job {job_id}: {e}")
            return {"error": str(e)}
