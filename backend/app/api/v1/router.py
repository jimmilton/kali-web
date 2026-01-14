"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    users,
    projects,
    assets,
    tools,
    jobs,
    vulnerabilities,
    credentials,
    workflows,
    reports,
    search,
    bulk,
    imports,
)

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(tools.router, prefix="/tools", tags=["Tools"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(vulnerabilities.router, prefix="/vulnerabilities", tags=["Vulnerabilities"])
api_router.include_router(credentials.router, prefix="/credentials", tags=["Credentials"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(bulk.router, prefix="/bulk", tags=["Bulk Operations"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(imports.router, prefix="/import", tags=["Import"])
