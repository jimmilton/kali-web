# kwebbie

Copyright 2025 milbert.ai

A web-based interface for running Kali Linux security tools with real-time output streaming.

## Quick Reference

**Start Services:**
```bash
sudo docker compose -f docker-compose.dev.yml up -d
```

**URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Database Admin: http://localhost:8080
- MinIO Console: http://localhost:9001

**Default Admin Account:**
On first startup, a default admin account is created. Check the backend logs for the generated credentials, or set them via environment variables.

## Project Structure

```
/home/jim/kwebbie/
├── backend/app/          # FastAPI backend
│   ├── api/v1/           # API endpoints
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── tools/            # Tool registry & parsers
│   └── websocket/        # Socket.IO handlers
├── backend/worker/       # Celery worker & tasks
├── frontend/app/         # Next.js pages
├── frontend/components/  # React components
├── frontend/hooks/       # Custom React hooks
├── frontend/lib/         # API client, utilities
└── tool-images/          # Tool Dockerfiles (11 tools)
```

## Current Status: ~60% Complete

**Read `IMPLEMENTATION_STATUS.md` for full details.**

### What's Working
- All Docker services (frontend, backend, worker, postgres, redis, minio)
- All frontend pages (17 pages)
- All backend API endpoints (18 endpoints)
- 11 tool Docker images (nmap, nuclei, gobuster, httpx, sqlmap, hydra, nikto, masscan, subfinder, ffuf, john)
- JWT authentication
- Real-time WebSocket output streaming
- Job management (run, cancel, retry)

### What's Missing (Priority Order)
1. **Output Parsers** - Parse nmap XML, nuclei JSON, etc. to auto-create assets/vulns
2. **Workflow Engine** - Multi-step automated workflows
3. **Report Generation** - PDF/DOCX reports
4. **More Tools** - amass, wpscan, metasploit, hashcat, etc.
5. **Integrations** - Slack, Jira, import from Nessus/Burp

## Key Files

| Purpose | File |
|---------|------|
| Docker Compose | `docker-compose.dev.yml` |
| Backend Entry | `backend/app/main.py` |
| Tool Registry | `backend/app/tools/registry.py` |
| API Routes | `backend/app/api/v1/*.py` |
| Celery Tasks | `backend/worker/tasks/tool_tasks.py` |
| Docker Runner | `backend/worker/docker_runner.py` |
| Frontend API | `frontend/lib/api.ts` |
| Auth Store | `frontend/stores/auth-store.ts` |

## Common Tasks

**Add a new tool:**
1. Create Dockerfile in `tool-images/<toolname>/Dockerfile`
2. Register in `backend/app/tools/registry.py`
3. Build image: `sudo docker build -t kali-<toolname> tool-images/<toolname>`

**Add a new page:**
1. Create in `frontend/app/(dashboard)/<route>/page.tsx`

**Add a new API endpoint:**
1. Add route in `backend/app/api/v1/<resource>.py`
2. Add schema in `backend/app/schemas/<resource>.py`

## Troubleshooting

**Containers not starting:**
```bash
sudo docker compose -f docker-compose.dev.yml logs -f
```

**Database issues:**
```bash
sudo docker exec kwebbie-postgres-1 psql -U $POSTGRES_USER -d kali_tools
```

**Rebuild after code changes:**
```bash
sudo docker compose -f docker-compose.dev.yml restart backend worker
```
