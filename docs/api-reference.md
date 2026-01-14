# API Quick Reference

Copyright 2025 milbert.ai

Base URL: `http://localhost/api/v1`

All endpoints except `/auth/login` and `/auth/register` require authentication via Bearer token.

## Authentication

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer {refresh_token}
```

### Current User
```http
GET /auth/me
Authorization: Bearer {access_token}
```

---

## Projects

### List Projects
```http
GET /projects
GET /projects?skip=0&limit=20&search=audit
```

### Create Project
```http
POST /projects
{
  "name": "Security Audit",
  "description": "Q1 2024 assessment",
  "settings": {}
}
```

### Get Project
```http
GET /projects/{project_id}
```

### Update Project
```http
PATCH /projects/{project_id}
{
  "name": "Updated Name"
}
```

### Delete Project
```http
DELETE /projects/{project_id}
```

---

## Tools

### List Tools
```http
GET /tools
GET /tools?category=reconnaissance
```

### Get Tool
```http
GET /tools/{slug}
```

### Execute Tool
```http
POST /tools/{slug}/execute
{
  "project_id": "uuid",
  "parameters": {
    "target": "192.168.1.1",
    "ports": "-p 1-1000"
  },
  "target_asset_ids": []
}
```

### Preview Command
```http
POST /tools/{slug}/preview
{
  "parameters": {
    "target": "192.168.1.1"
  }
}
```

---

## Jobs

### List Jobs
```http
GET /jobs
GET /jobs?project_id={id}&status=running
```

### Get Job
```http
GET /jobs/{job_id}
```

### Get Job Output
```http
GET /jobs/{job_id}/output
```

### Cancel Job
```http
POST /jobs/{job_id}/cancel
```

---

## Assets

### List Assets
```http
GET /projects/{project_id}/assets
GET /projects/{project_id}/assets?type=host&search=192.168
```

### Create Asset
```http
POST /projects/{project_id}/assets
{
  "type": "host",
  "value": "192.168.1.1",
  "metadata": {
    "os": "Linux"
  }
}
```

### Get Asset
```http
GET /projects/{project_id}/assets/{asset_id}
```

### Update Asset
```http
PATCH /projects/{project_id}/assets/{asset_id}
{
  "tags": ["critical", "production"]
}
```

### Delete Asset
```http
DELETE /projects/{project_id}/assets/{asset_id}
```

### Get Asset Graph
```http
GET /projects/{project_id}/assets/graph
```

### Create Asset Relation
```http
POST /projects/{project_id}/assets/relations
{
  "parent_id": "uuid",
  "child_id": "uuid",
  "relation_type": "has_service"
}
```

---

## Vulnerabilities

### List Vulnerabilities
```http
GET /projects/{project_id}/vulnerabilities
GET /projects/{project_id}/vulnerabilities?severity=high&status=open
```

### Create Vulnerability
```http
POST /projects/{project_id}/vulnerabilities
{
  "title": "SQL Injection",
  "description": "Found SQL injection in login form",
  "severity": "high",
  "asset_id": "uuid"
}
```

### Update Vulnerability
```http
PATCH /projects/{project_id}/vulnerabilities/{vuln_id}
{
  "status": "confirmed",
  "notes": "Verified manually"
}
```

---

## Credentials

### List Credentials
```http
GET /projects/{project_id}/credentials
```

### Create Credential
```http
POST /projects/{project_id}/credentials
{
  "credential_type": "password",
  "username": "admin",
  "password": "secret123",
  "service": "ssh",
  "asset_id": "uuid"
}
```

### Get Credential (with password)
```http
GET /projects/{project_id}/credentials/{cred_id}/reveal
```

---

## Workflows

### List Workflows
```http
GET /workflows
```

### Create Workflow
```http
POST /workflows
{
  "name": "Full Scan",
  "description": "Complete security scan",
  "definition": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### Execute Workflow
```http
POST /workflows/{workflow_id}/execute
{
  "project_id": "uuid",
  "parameters": {
    "target": "example.com"
  }
}
```

### Get Workflow Run
```http
GET /workflows/runs/{run_id}
```

### Approve Manual Step
```http
POST /workflows/runs/{run_id}/approve
{
  "approved": true,
  "notes": "Looks good"
}
```

---

## Reports

### Generate Report
```http
POST /projects/{project_id}/reports
{
  "name": "Security Assessment",
  "format": "pdf",
  "include_assets": true,
  "include_vulnerabilities": true,
  "include_credentials": false
}
```

### List Reports
```http
GET /projects/{project_id}/reports
```

### Download Report
```http
GET /projects/{project_id}/reports/{report_id}/download
```

---

## WebSocket Events

Connect to: `ws://localhost/ws?token={access_token}`

### Job Events
```json
{"event": "job_started", "data": {"job_id": "...", "tool": "nmap"}}
{"event": "job_output", "data": {"job_id": "...", "content": "...", "type": "stdout"}}
{"event": "job_completed", "data": {"job_id": "...", "status": "completed"}}
```

### Workflow Events
```json
{"event": "workflow_started", "data": {"run_id": "..."}}
{"event": "workflow_node_started", "data": {"run_id": "...", "node_id": "..."}}
{"event": "workflow_approval_required", "data": {"run_id": "...", "message": "..."}}
{"event": "workflow_completed", "data": {"run_id": "...", "status": "completed"}}
```

---

## Error Responses

```json
{
  "detail": "Error message"
}
```

Common HTTP status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Rate Limiting

Default limits:
- 60 requests per minute
- 1000 requests per hour

Headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`
