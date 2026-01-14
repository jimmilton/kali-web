# Security Tools Reference

Copyright 2025 milbert.ai

This document describes the security tools available in kwebbie.

## Network Scanning

### Nmap

**Category**: Reconnaissance
**Purpose**: Network exploration and security auditing

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | IP, hostname, or CIDR | Required |
| ports | String | Port specification | -p- |
| scan_type | Select | Type of scan | -sV |
| scripts | Select | NSE script categories | - |
| timing | Select | Timing template (T0-T5) | -T4 |

**Example**:
```bash
nmap 192.168.1.0/24 -p 22,80,443 -sV -T4
```

**Output**: XML format, parsed to create host and service assets

---

### Masscan

**Category**: Reconnaissance
**Purpose**: High-speed port scanner

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | IP or CIDR range | Required |
| ports | String | Port specification | 1-65535 |
| rate | Integer | Packets per second | 10000 |

**Example**:
```bash
masscan 10.0.0.0/8 -p 80,443 --rate 100000
```

**Output**: JSON format, creates host and port assets

---

## Subdomain Enumeration

### Subfinder

**Category**: Reconnaissance
**Purpose**: Passive subdomain discovery

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| domain | Target | Target domain | Required |
| sources | Multi-select | Data sources | All |
| recursive | Boolean | Recursive enumeration | false |

**Example**:
```bash
subfinder -d example.com -all
```

**Output**: JSON format, creates subdomain assets

---

### Amass

**Category**: Reconnaissance
**Purpose**: In-depth subdomain enumeration

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| domain | Target | Target domain | Required |
| mode | Select | enum/intel | enum |
| passive | Boolean | Passive only | false |

**Example**:
```bash
amass enum -d example.com -passive
```

---

## Web Application Testing

### Nuclei

**Category**: Vulnerability Scanning
**Purpose**: Template-based vulnerability scanner

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | URL or host | Required |
| templates | Multi-select | Template categories | - |
| severity | Multi-select | Severity filter | all |
| rate_limit | Integer | Requests per second | 150 |

**Example**:
```bash
nuclei -u https://example.com -t cves/ -severity high,critical
```

**Output**: JSON format, creates vulnerability findings

---

### Nikto

**Category**: Vulnerability Scanning
**Purpose**: Web server scanner

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | Target URL | Required |
| tuning | Select | Scan tuning | - |
| plugins | String | Plugin selection | - |

**Example**:
```bash
nikto -h https://example.com
```

**Output**: JSON format, creates vulnerability findings

---

### HTTPX

**Category**: Web Application
**Purpose**: HTTP toolkit and prober

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | URL or host list | Required |
| probes | Multi-select | HTTP probes | status-code,title |
| tech_detect | Boolean | Technology detection | true |

**Example**:
```bash
httpx -u https://example.com -status-code -title -tech-detect
```

**Output**: JSON format, creates URL assets with metadata

---

## Directory/File Discovery

### Gobuster

**Category**: Web Application
**Purpose**: Directory and file brute-forcing

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| url | Target | Target URL | Required |
| wordlist | Wordlist | Wordlist path | - |
| extensions | String | File extensions | - |
| threads | Integer | Concurrent threads | 10 |

**Example**:
```bash
gobuster dir -u https://example.com -w /wordlists/common.txt -x php,html
```

**Output**: Text format, creates directory/file assets

---

### FFUF

**Category**: Web Application
**Purpose**: Fast web fuzzer

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| url | Target | Target URL with FUZZ | Required |
| wordlist | Wordlist | Wordlist path | - |
| method | Select | HTTP method | GET |
| filter_status | String | Filter by status | - |

**Example**:
```bash
ffuf -u https://example.com/FUZZ -w wordlist.txt -fc 404
```

**Output**: JSON format, creates discovered endpoint assets

---

### Feroxbuster

**Category**: Web Application
**Purpose**: Recursive content discovery

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| url | Target | Target URL | Required |
| wordlist | Wordlist | Wordlist path | - |
| depth | Integer | Recursion depth | 4 |
| threads | Integer | Concurrent threads | 50 |

**Example**:
```bash
feroxbuster -u https://example.com -w wordlist.txt --depth 3
```

---

## Password Attacks

### Hydra

**Category**: Password Attacks
**Purpose**: Network login cracker

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | Target host | Required |
| service | Select | Service to attack | ssh |
| username | String | Username or file | - |
| password_list | Wordlist | Password wordlist | - |
| port | Port | Service port | - |

**Example**:
```bash
hydra -l admin -P passwords.txt ssh://192.168.1.1
```

**Output**: Text format, creates credential findings

---

## SQL Injection

### SQLMap

**Category**: Web Application
**Purpose**: SQL injection detection and exploitation

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| url | Target | Target URL | Required |
| data | String | POST data | - |
| level | Select | Test level (1-5) | 1 |
| risk | Select | Risk level (1-3) | 1 |
| technique | Multi-select | SQL techniques | - |

**Example**:
```bash
sqlmap -u "https://example.com/page?id=1" --level 3 --risk 2
```

---

## CMS Scanning

### WPScan

**Category**: Web Application
**Purpose**: WordPress security scanner

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| url | Target | WordPress URL | Required |
| enumerate | Multi-select | Enumeration options | - |
| api_token | Secret | WPScan API token | - |

**Example**:
```bash
wpscan --url https://example.com -e vp,vt,u
```

**Output**: JSON format, creates WordPress-specific vulnerabilities

---

## SSL/TLS Analysis

### SSLScan

**Category**: Reconnaissance
**Purpose**: SSL/TLS configuration analysis

**Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | Target | Host:port | Required |
| show_certs | Boolean | Show certificates | true |

**Example**:
```bash
sslscan example.com:443
```

---

## Output Parsers

Each tool has an associated parser that processes output and creates:

| Parser | Creates |
|--------|---------|
| nmap_parser | Hosts, ports, services, vulnerabilities |
| nuclei_parser | Vulnerabilities |
| subfinder_parser | Subdomain assets |
| masscan_parser | Hosts, ports |
| httpx_parser | URLs, technologies |
| gobuster_parser | Directories, files |
| ffuf_parser | Endpoints |
| nikto_parser | Vulnerabilities |
| hydra_parser | Credentials |

## Adding Custom Tools

To add a new tool:

1. **Define Tool** in `backend/app/tools/registry.py`:
```python
register_tool(ToolDefinition(
    slug="my-tool",
    name="My Tool",
    description="Tool description",
    category=ToolCategory.RECONNAISSANCE,
    docker_image="my-tool:latest",
    command_template="my-tool {target} {options}",
    parameters=[...],
    output=ToolOutput(format="json", parser="my_parser"),
))
```

2. **Create Parser** in `backend/app/tools/parsers/my_parser.py`

3. **Register Parser** in `backend/app/tools/parsers/__init__.py`

4. **Build Docker Image** with the tool installed
