# kwebbie

Copyright 2025 milbert.ai

A professional web interface for Kali Linux security tools with real-time output, vulnerability management, and automated workflows.

## Features

- **20+ Security Tools** - Pre-configured tools including nmap, nuclei, sqlmap, gobuster, hydra, and more
- **Real-time Output** - Watch tool execution live with WebSocket streaming
- **Project Management** - Organize assessments with scope definition and team collaboration
- **Asset Tracking** - Automatically discover and track hosts, domains, URLs, and services
- **Vulnerability Management** - Track, classify, and remediate findings
- **Credential Storage** - Securely store and manage discovered credentials
- **Workflow Automation** - Build automated scan pipelines with visual workflow builder
- **Professional Reports** - Generate PDF/DOCX reports for clients

## Quick Start

### Prerequisites

- Docker and Docker Compose
- 4GB+ RAM recommended
- Modern web browser

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/milbert-ai/kwebbie.git
cd kwebbie
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start the development environment:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Deployment

```bash
docker-compose up -d
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx                                │
│                    (Reverse Proxy)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Frontend  │   │   Backend   │   │  WebSocket  │
│  (Next.js)  │   │  (FastAPI)  │   │  (Socket.IO)│
└─────────────┘   └──────┬──────┘   └──────┬──────┘
                         │                 │
          ┌──────────────┼─────────────────┤
          │              │                 │
          ▼              ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  PostgreSQL │   │    Redis    │   │    MinIO    │
│  (Database) │   │   (Cache)   │   │  (Storage)  │
└─────────────┘   └──────┬──────┘   └─────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   Celery    │
                  │  (Worker)   │
                  └──────┬──────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Docker Executor   │
              │   (Tool Containers) │
              └─────────────────────┘
```

## Project Structure

```
kwebbie/
├── frontend/           # Next.js frontend application
├── backend/            # FastAPI backend application
├── tool-images/        # Docker images for security tools
├── nginx/              # Nginx configuration
├── scripts/            # Utility scripts
└── docker-compose.yml  # Production Docker Compose
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379` |
| `SECRET_KEY` | JWT secret key | (required) |
| `MINIO_ROOT_USER` | MinIO admin user | `minio` |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | (required) |

## API Documentation

API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc) when running the backend.

## Security Considerations

- All tool execution happens in isolated Docker containers
- Network namespaces prevent tools from accessing internal services
- Resource limits (CPU, memory, time) are enforced per job
- Credentials are encrypted at rest
- Role-based access control (RBAC) for all endpoints
- Audit logging for all actions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Copyright 2025 milbert.ai. All rights reserved.
