"""WebSocket manager using Socket.IO for real-time communication."""

import logging
from typing import Dict, Set
from uuid import UUID

import socketio

from app.config import settings
from app.core.security import verify_token

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins,
    logger=True,
    engineio_logger=True if settings.debug else False,
)

# Track connected clients and their subscriptions
connected_clients: Dict[str, dict] = {}  # sid -> {user_id, subscriptions: set()}
job_subscribers: Dict[str, Set[str]] = {}  # job_id -> set of sids
project_subscribers: Dict[str, Set[str]] = {}  # project_id -> set of sids


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection."""
    logger.info(f"Client connecting: {sid}")

    # Authenticate using token
    token = None
    if auth and "token" in auth:
        token = auth["token"]
    elif "HTTP_AUTHORIZATION" in environ:
        auth_header = environ["HTTP_AUTHORIZATION"]
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        logger.warning(f"Client {sid} connection rejected: no token")
        return False

    payload = verify_token(token)
    if not payload:
        logger.warning(f"Client {sid} connection rejected: invalid token")
        return False

    user_id = payload.get("sub")
    connected_clients[sid] = {
        "user_id": user_id,
        "subscriptions": set(),
    }

    logger.info(f"Client {sid} connected as user {user_id}")
    return True


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")

    if sid in connected_clients:
        client = connected_clients[sid]

        # Remove from all subscriptions
        for sub in client["subscriptions"]:
            if sub.startswith("job:"):
                job_id = sub[4:]
                if job_id in job_subscribers:
                    job_subscribers[job_id].discard(sid)
            elif sub.startswith("project:"):
                project_id = sub[8:]
                if project_id in project_subscribers:
                    project_subscribers[project_id].discard(sid)

        del connected_clients[sid]


@sio.event
async def subscribe_job(sid, data):
    """Subscribe to job updates."""
    job_id = data.get("job_id")
    if not job_id:
        return {"error": "job_id required"}

    if sid not in connected_clients:
        return {"error": "not authenticated"}

    # Add subscription
    sub_key = f"job:{job_id}"
    connected_clients[sid]["subscriptions"].add(sub_key)

    if job_id not in job_subscribers:
        job_subscribers[job_id] = set()
    job_subscribers[job_id].add(sid)

    logger.info(f"Client {sid} subscribed to job {job_id}")

    # Join the room for this job
    await sio.enter_room(sid, f"job:{job_id}")

    return {"success": True}


@sio.event
async def unsubscribe_job(sid, data):
    """Unsubscribe from job updates."""
    job_id = data.get("job_id")
    if not job_id:
        return {"error": "job_id required"}

    if sid in connected_clients:
        sub_key = f"job:{job_id}"
        connected_clients[sid]["subscriptions"].discard(sub_key)

    if job_id in job_subscribers:
        job_subscribers[job_id].discard(sid)

    await sio.leave_room(sid, f"job:{job_id}")

    return {"success": True}


@sio.event
async def subscribe_project(sid, data):
    """Subscribe to project updates."""
    project_id = data.get("project_id")
    if not project_id:
        return {"error": "project_id required"}

    if sid not in connected_clients:
        return {"error": "not authenticated"}

    sub_key = f"project:{project_id}"
    connected_clients[sid]["subscriptions"].add(sub_key)

    if project_id not in project_subscribers:
        project_subscribers[project_id] = set()
    project_subscribers[project_id].add(sid)

    await sio.enter_room(sid, f"project:{project_id}")

    return {"success": True}


@sio.event
async def job_input(sid, data):
    """Handle input to a running job (for interactive tools)."""
    job_id = data.get("job_id")
    input_data = data.get("input")

    if not job_id or input_data is None:
        return {"error": "job_id and input required"}

    # TODO: Send input to the running container
    logger.info(f"Job {job_id} received input from {sid}: {input_data[:50]}...")

    return {"success": True}


async def emit_job_output(job_id: str, output: str, output_type: str = "stdout"):
    """Emit job output to all subscribers."""
    await sio.emit(
        "job_output",
        {
            "job_id": job_id,
            "output": output,
            "type": output_type,
        },
        room=f"job:{job_id}",
    )


async def emit_job_status(job_id: str, status: str, details: dict = None):
    """Emit job status update to all subscribers."""
    await sio.emit(
        "job_status",
        {
            "job_id": job_id,
            "status": status,
            "details": details or {},
        },
        room=f"job:{job_id}",
    )


async def emit_project_update(project_id: str, event_type: str, data: dict):
    """Emit project update to all subscribers."""
    await sio.emit(
        "project_update",
        {
            "project_id": project_id,
            "event_type": event_type,
            "data": data,
        },
        room=f"project:{project_id}",
    )


async def emit_notification(user_id: str, notification: dict):
    """Emit notification to a specific user."""
    # Find all sids for this user
    for sid, client in connected_clients.items():
        if client["user_id"] == user_id:
            await sio.emit("notification", notification, room=sid)
