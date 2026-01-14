# kwebbie Documentation

Copyright 2025 milbert.ai

A web-based interface for managing and executing Kali Linux security tools with workflow automation, asset tracking, and vulnerability management.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Features](#features)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [User Guide](#user-guide)
- [Development](#development)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- 4GB+ RAM recommended
- Linux host (for Docker socket access)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd kwebbie
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost
- API: http://localhost/api/v1
- API Docs: http://localhost/api/docs
- MinIO Console: http://localhost:9001

### Default Credentials

- **MinIO**: minioadmin / minioadmin
- **Database**: kali / kali_secret

## Architecture

```
+----------------+     +----------------+     +----------------+
|    Frontend    |---->|     Nginx      |---->|    Backend     |
|   (Next.js)    |     |  (Reverse Proxy)|    |   (FastAPI)    |
+----------------+     +----------------+     +-------+--------+
                                                      |
                       +----------------+     +-------v--------+
                       |     Redis      |<----|    Celery      |
                       | (Task Queue)   |     |   (Workers)    |
                       +----------------+     +-------+--------+
                                                      |
                       +----------------+     +-------v--------+
                       |   PostgreSQL   |     |    Docker      |
                       |   (Database)   |     | (Tool Execution)|
                       +----------------+     +----------------+

                       +----------------+
                       |     MinIO      |
                       | (File Storage) |
                       +----------------+
```

### Components

| Service | Purpose | Port |
|---------|---------|------|
| nginx | Reverse proxy, SSL termination | 80, 443 |
| frontend | Next.js web application | 3000 |
| backend | FastAPI REST API | 8000 |
| worker | Celery task workers | - |
| beat | Celery scheduler | - |
| postgres | PostgreSQL database | 5432 |
| redis | Message broker & cache | 6379 |
| minio | S3-compatible storage | 9000, 9001 |

## Features

### Project Management
- Create and manage security testing projects
- Organize assets, scans, and findings by project
- Project-level settings and configurations

### Tool Execution
- **15+ Kali Linux tools** pre-configured:
  - Nmap, Masscan (Network scanning)
  - Nuclei, Nikto (Vulnerability scanning)
  - Subfinder, Amass (Subdomain enumeration)
  - Gobuster, FFUF, Feroxbuster (Directory brute-forcing)
  - HTTPX (HTTP probing)
  - Hydra (Password attacks)
  - SQLMap (SQL injection)
  - WPScan (WordPress scanning)
  - SSLScan (SSL/TLS analysis)

### Workflow Automation
- **Visual Workflow Builder** with drag-and-drop nodes
- Node types:
  - **Tool**: Execute security tools
  - **Condition**: Branch based on results
  - **Parallel**: Run multiple tools simultaneously
  - **Loop**: Iterate over targets
  - **Delay**: Wait between steps
  - **Manual**: Require user approval
  - **Notification**: Send alerts

### Asset Management
- Automatic asset discovery from scan results
- Asset types: Hosts, Domains, URLs, Services
- Asset relationship graph visualization
- Asset tagging and categorization

### Vulnerability Tracking
- Automatic vulnerability creation from scan results
- Severity classification (Critical, High, Medium, Low, Info)
- CVSS scoring support
- Vulnerability deduplication by fingerprint

### Credential Management
- Secure storage with encryption
- Discovered credentials from tools (Hydra, etc.)
- Support for passwords, hashes, and API keys

### Reporting
- PDF and HTML report generation
- Customizable report templates
- Export findings and assets

## API Reference

The API follows REST conventions and uses JWT authentication.

### Authentication

```bash
# Register
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}

# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "secure_password"
}
# Returns: { "access_token": "...", "refresh_token": "..." }
```

### Projects

```bash
# List projects
GET /api/v1/projects

# Create project
POST /api/v1/projects
{
  "name": "Security Audit",
  "description": "Q1 2024 security assessment"
}

# Get project
GET /api/v1/projects/{id}
```

### Tools

```bash
# List available tools
GET /api/v1/tools

# Get tool definition
GET /api/v1/tools/{slug}

# Execute tool
POST /api/v1/tools/{slug}/execute
{
  "project_id": "uuid",
  "parameters": {
    "target": "192.168.1.1",
    "ports": "-p 1-1000"
  }
}
```

### Jobs

```bash
# List jobs
GET /api/v1/jobs?project_id={id}

# Get job details
GET /api/v1/jobs/{id}

# Get job output
GET /api/v1/jobs/{id}/output

# Cancel job
POST /api/v1/jobs/{id}/cancel
```

### Assets

```bash
# List assets
GET /api/v1/projects/{id}/assets

# Create asset
POST /api/v1/projects/{id}/assets
{
  "type": "host",
  "value": "192.168.1.1",
  "metadata": {}
}

# Get asset graph
GET /api/v1/projects/{id}/assets/graph
```

### Vulnerabilities

```bash
# List vulnerabilities
GET /api/v1/projects/{id}/vulnerabilities

# Update vulnerability
PATCH /api/v1/projects/{id}/vulnerabilities/{vuln_id}
{
  "status": "confirmed",
  "notes": "Verified manually"
}
```

### Workflows

```bash
# List workflows
GET /api/v1/workflows

# Create workflow
POST /api/v1/workflows
{
  "name": "Full Scan",
  "description": "Complete security scan",
  "definition": { ... }
}

# Execute workflow
POST /api/v1/workflows/{id}/execute
{
  "project_id": "uuid",
  "parameters": {
    "target": "example.com"
  }
}

# Approve manual step
POST /api/v1/workflows/runs/{run_id}/approve
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `SECRET_KEY` | JWT signing key | - |
| `ENCRYPTION_KEY` | Fernet encryption key | - |
| `MINIO_ENDPOINT` | MinIO server address | minio:9000 |
| `MINIO_ACCESS_KEY` | MinIO access key | minioadmin |
| `MINIO_SECRET_KEY` | MinIO secret key | minioadmin |

### Generating Encryption Key

```bash
docker exec kwebbie-backend-1 python -c \
  "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### SSL Configuration

Place SSL certificates in `nginx/ssl/`:
- `nginx/ssl/cert.pem`
- `nginx/ssl/key.pem`

## User Guide

### Creating a Project

1. Navigate to **Projects** > **New Project**
2. Enter project name and description
3. Configure project settings
4. Click **Create**

### Running a Scan

1. Go to **Tools** page
2. Select a tool (e.g., Nmap)
3. Choose target project
4. Configure parameters
5. Click **Execute**

### Building a Workflow

1. Navigate to **Workflows** > **New Workflow**
2. Drag nodes from the sidebar
3. Connect nodes to define flow
4. Configure each node's parameters
5. Save and execute

### Viewing Results

- **Jobs**: Real-time output and status
- **Assets**: Auto-discovered hosts, domains, services
- **Vulnerabilities**: Findings with severity ratings
- **Reports**: Generate PDF/HTML summaries

## Development

### Project Structure

```
kwebbie/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── tools/         # Tool registry & parsers
│   │   └── workflow/      # Workflow engine
│   ├── worker/            # Celery tasks
│   └── tests/             # Test suite
├── frontend/
│   ├── app/               # Next.js pages
│   ├── components/        # React components
│   ├── hooks/             # Custom hooks
│   └── lib/               # Utilities
└── docs/                  # Documentation
```

### Running Tests

```bash
# Backend tests
docker exec kwebbie-backend-1 python -m pytest tests/ -v

# With coverage
docker exec kwebbie-backend-1 python -m pytest tests/ --cov=app
```

### Adding a New Tool

1. Add tool definition in `backend/app/tools/registry.py`
2. Create parser in `backend/app/tools/parsers/`
3. Build Docker image for the tool
4. Register parser in `backend/app/tools/parsers/__init__.py`

### API Documentation

Interactive API docs available at:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`
