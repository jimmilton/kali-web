# kwebbie - Single Image Deployment

Copyright 2025 milbert.ai

## Quick Start

### Build the image

```bash
docker build -t kwebbie .
```

### Run the container

```bash
docker run -d \
  --name kwebbie \
  -p 8080:8080 \
  -v kwebbie-data:/data \
  kwebbie
```

### Access the application

Open http://localhost:8080 in your browser.

---

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | HTTP port |
| `SECRET_KEY` | (auto-generated) | JWT signing key |
| `DEBUG` | `false` | Enable debug mode |
| `DATA_DIR` | `/data` | Data storage path |

### Example with custom settings

```bash
docker run -d \
  --name kwebbie \
  -p 80:8080 \
  -v /srv/kwebbie:/data \
  -e SECRET_KEY=your-secure-secret-key \
  -e DEBUG=false \
  kwebbie
```

---

## Data Persistence

All data is stored in `/data` inside the container:

- `/data/kwebbie.db` - SQLite database
- `/data/uploads/` - Uploaded files
- `/data/reports/` - Generated reports
- `/data/outputs/` - Tool execution outputs

**Always mount a volume to `/data` for persistence.**

---

## Included Security Tools

| Category | Tools |
|----------|-------|
| Reconnaissance | nmap, masscan, subfinder, httpx, whatweb |
| Vulnerability Scanning | nuclei, nikto, sslscan |
| Web Application | gobuster, ffuf, dirb, wfuzz, sqlmap |
| Password Attacks | hydra, john |
| CMS Scanning | wpscan |

---

## Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Disk | 5 GB | 20 GB |

---

## Backup

Backup the data volume:

```bash
docker run --rm \
  -v kwebbie-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/kwebbie-backup.tar.gz -C /data .
```

Restore:

```bash
docker run --rm \
  -v kwebbie-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/kwebbie-backup.tar.gz -C /data
```

---

## Logs

View logs:

```bash
docker logs -f kwebbie
```

---

## Update

```bash
docker pull kwebbie:latest
docker stop kwebbie
docker rm kwebbie
docker run -d --name kwebbie -p 8080:8080 -v kwebbie-data:/data kwebbie:latest
```

---

## Troubleshooting

### Container won't start

Check logs:
```bash
docker logs kwebbie
```

### Tools not working

Verify tools are installed:
```bash
docker exec kwebbie which nmap nuclei gobuster
```

### Database issues

Reset database (WARNING: deletes all data):
```bash
docker exec kwebbie rm /data/kwebbie.db
docker restart kwebbie
```
