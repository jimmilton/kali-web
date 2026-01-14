"""Tool registry with all tool definitions.

Copyright 2025 milbert.ai
"""

from typing import Dict, List, Optional

from app.schemas.tool import (
    ParameterType,
    ToolCategory,
    ToolDefinition,
    ToolOutput,
    ToolParameter,
)

# Global tool registry
_tools: Dict[str, ToolDefinition] = {}


def register_tool(tool: ToolDefinition) -> None:
    """Register a tool in the registry."""
    _tools[tool.slug] = tool


def get_tool(slug: str) -> Optional[ToolDefinition]:
    """Get a tool by slug."""
    return _tools.get(slug)


def list_all_tools() -> List[ToolDefinition]:
    """List all registered tools."""
    return list(_tools.values())


def get_tools_by_category(category: ToolCategory) -> List[ToolDefinition]:
    """Get tools by category."""
    return [t for t in _tools.values() if t.category == category]


# =============================================================================
# RECONNAISSANCE TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="nmap",
    name="Nmap",
    description="Network exploration and security auditing tool",
    category=ToolCategory.RECONNAISSANCE,
    version="7.94",
    docker_image="kali-nmap",
    command_template="nmap {target} {ports} {scan_type} {scripts} {timing} {output}",
    parameters=[
        ToolParameter(
            name="target",
            label="Target",
            type=ParameterType.TARGET,
            description="Target IP, hostname, or CIDR range",
            required=True,
            placeholder="192.168.1.1 or example.com",
        ),
        ToolParameter(
            name="ports",
            label="Ports",
            type=ParameterType.STRING,
            description="Port specification (-p)",
            default="-p-",
            placeholder="-p 80,443 or -p 1-1000 or -p-",
        ),
        ToolParameter(
            name="scan_type",
            label="Scan Type",
            type=ParameterType.SELECT,
            description="Type of scan to perform",
            default="-sV",
            options=[
                {"value": "-sS", "label": "SYN Scan (Stealth)", "description": "Default scan, requires root"},
                {"value": "-sT", "label": "TCP Connect Scan", "description": "Full TCP connection"},
                {"value": "-sV", "label": "Version Detection", "description": "Detect service versions"},
                {"value": "-sU", "label": "UDP Scan", "description": "Scan UDP ports"},
                {"value": "-sA", "label": "ACK Scan", "description": "Firewall rule detection"},
            ],
        ),
        ToolParameter(
            name="scripts",
            label="Scripts",
            type=ParameterType.STRING,
            description="NSE scripts to run (--script)",
            placeholder="--script vuln or --script default",
            advanced=True,
        ),
        ToolParameter(
            name="timing",
            label="Timing",
            type=ParameterType.SELECT,
            description="Timing template",
            default="-T4",
            options=[
                {"value": "-T0", "label": "Paranoid", "description": "Very slow, IDS evasion"},
                {"value": "-T1", "label": "Sneaky", "description": "Slow, IDS evasion"},
                {"value": "-T2", "label": "Polite", "description": "Slower than normal"},
                {"value": "-T3", "label": "Normal", "description": "Default"},
                {"value": "-T4", "label": "Aggressive", "description": "Faster"},
                {"value": "-T5", "label": "Insane", "description": "Fastest"},
            ],
            advanced=True,
        ),
        ToolParameter(
            name="output",
            label="Output Format",
            type=ParameterType.STRING,
            description="Output format",
            default="-oX -",
            advanced=True,
        ),
    ],
    output=ToolOutput(
        format="xml",
        parser="nmap_parser",
        creates_assets=True,
        creates_vulnerabilities=True,
    ),
    default_timeout=3600,
    requires_root=True,
    tags=["network", "scanner", "ports", "services"],
))

register_tool(ToolDefinition(
    slug="masscan",
    name="Masscan",
    description="Fast port scanner, can scan the entire Internet in under 6 minutes",
    category=ToolCategory.RECONNAISSANCE,
    version="1.3.2",
    docker_image="kali-masscan",
    command_template="masscan {target} {ports} --rate {rate} -oJ -",
    parameters=[
        ToolParameter(
            name="target",
            label="Target",
            type=ParameterType.TARGET,
            description="Target IP or CIDR range",
            required=True,
        ),
        ToolParameter(
            name="ports",
            label="Ports",
            type=ParameterType.STRING,
            description="Port specification (-p)",
            default="-p 1-65535",
            required=True,
        ),
        ToolParameter(
            name="rate",
            label="Packet Rate",
            type=ParameterType.INTEGER,
            description="Packets per second",
            default=10000,
            min_value=100,
            max_value=10000000,
        ),
    ],
    output=ToolOutput(format="json", parser="masscan_parser", creates_assets=True),
    default_timeout=3600,
    requires_root=True,
    tags=["network", "fast", "ports"],
))

register_tool(ToolDefinition(
    slug="subfinder",
    name="Subfinder",
    description="Subdomain discovery tool using passive sources",
    category=ToolCategory.RECONNAISSANCE,
    version="2.6.3",
    docker_image="kali-subfinder",
    command_template="subfinder -d {domain} {sources} -silent -json",
    parameters=[
        ToolParameter(
            name="domain",
            label="Domain",
            type=ParameterType.STRING,
            description="Target domain",
            required=True,
            placeholder="example.com",
        ),
        ToolParameter(
            name="sources",
            label="Sources",
            type=ParameterType.STRING,
            description="Specific sources to use (-sources)",
            placeholder="-sources shodan,censys",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="subfinder_parser", creates_assets=True),
    default_timeout=1800,
    tags=["subdomain", "passive", "recon"],
))

register_tool(ToolDefinition(
    slug="httpx",
    name="HTTPx",
    description="Fast HTTP probing tool",
    category=ToolCategory.RECONNAISSANCE,
    version="1.3.7",
    docker_image="kali-httpx",
    command_template="httpx-toolkit -l {input} {probes} -json",
    parameters=[
        ToolParameter(
            name="input",
            label="Input File/URL",
            type=ParameterType.STRING,
            description="Input file with URLs or single URL",
            required=True,
        ),
        ToolParameter(
            name="probes",
            label="Probes",
            type=ParameterType.MULTI_SELECT,
            description="Information to probe",
            options=[
                {"value": "-status-code", "label": "Status Code"},
                {"value": "-title", "label": "Page Title"},
                {"value": "-tech-detect", "label": "Technology Detection"},
                {"value": "-server", "label": "Server Header"},
                {"value": "-content-length", "label": "Content Length"},
            ],
        ),
    ],
    output=ToolOutput(format="json", parser="httpx_parser", creates_assets=True),
    default_timeout=1800,
    tags=["http", "probe", "web"],
))

# =============================================================================
# VULNERABILITY SCANNING TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="nuclei",
    name="Nuclei",
    description="Fast and customizable vulnerability scanner based on templates",
    category=ToolCategory.VULNERABILITY_SCANNING,
    version="3.1.0",
    docker_image="kali-nuclei",
    command_template="nuclei -u {target} {templates} {severity} {tags} -json",
    parameters=[
        ToolParameter(
            name="target",
            label="Target URL",
            type=ParameterType.STRING,
            description="Target URL to scan",
            required=True,
            placeholder="https://example.com",
        ),
        ToolParameter(
            name="templates",
            label="Templates",
            type=ParameterType.STRING,
            description="Template directories or files (-t)",
            default="-t cves/ -t vulnerabilities/",
            placeholder="-t cves/ or -t /path/to/template.yaml",
        ),
        ToolParameter(
            name="severity",
            label="Severity Filter",
            type=ParameterType.MULTI_SELECT,
            description="Filter templates by severity (-s)",
            options=[
                {"value": "critical", "label": "Critical"},
                {"value": "high", "label": "High"},
                {"value": "medium", "label": "Medium"},
                {"value": "low", "label": "Low"},
                {"value": "info", "label": "Info"},
            ],
        ),
        ToolParameter(
            name="tags",
            label="Tags",
            type=ParameterType.STRING,
            description="Filter by tags (-tags)",
            placeholder="-tags cve,oast",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="nuclei_parser", creates_vulnerabilities=True),
    default_timeout=7200,
    tags=["vulnerability", "templates", "automated"],
))

register_tool(ToolDefinition(
    slug="nikto",
    name="Nikto",
    description="Web server scanner for dangerous files, outdated software, and misconfigurations",
    category=ToolCategory.VULNERABILITY_SCANNING,
    version="2.5.0",
    docker_image="kali-nikto",
    command_template="nikto -h {host} {port} {ssl} {tuning} -Format json",
    parameters=[
        ToolParameter(
            name="host",
            label="Host",
            type=ParameterType.STRING,
            description="Target host",
            required=True,
            placeholder="example.com or 192.168.1.1",
        ),
        ToolParameter(
            name="port",
            label="Port",
            type=ParameterType.PORT,
            description="Target port (-p)",
            default=80,
        ),
        ToolParameter(
            name="ssl",
            label="Use SSL",
            type=ParameterType.BOOLEAN,
            description="Use SSL (-ssl)",
            default=False,
        ),
        ToolParameter(
            name="tuning",
            label="Tuning",
            type=ParameterType.STRING,
            description="Scan tuning options (-Tuning)",
            placeholder="-Tuning 123bde",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="nikto_parser", creates_vulnerabilities=True),
    default_timeout=3600,
    tags=["web", "scanner", "vulnerability"],
))

# =============================================================================
# WEB APPLICATION TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="gobuster",
    name="Gobuster",
    description="Directory/file brute-forcing tool",
    category=ToolCategory.WEB_APPLICATION,
    version="3.6.0",
    docker_image="kali-gobuster",
    command_template="gobuster dir -u {url} -w {wordlist} {extensions} {threads} -o -",
    parameters=[
        ToolParameter(
            name="url",
            label="URL",
            type=ParameterType.STRING,
            description="Target URL",
            required=True,
            placeholder="https://example.com",
        ),
        ToolParameter(
            name="wordlist",
            label="Wordlist",
            type=ParameterType.WORDLIST,
            description="Wordlist to use (-w)",
            default="/usr/share/wordlists/dirb/common.txt",
        ),
        ToolParameter(
            name="extensions",
            label="Extensions",
            type=ParameterType.STRING,
            description="File extensions to search for (-x)",
            placeholder="-x php,html,txt",
        ),
        ToolParameter(
            name="threads",
            label="Threads",
            type=ParameterType.INTEGER,
            description="Number of concurrent threads (-t)",
            default=10,
            min_value=1,
            max_value=100,
        ),
    ],
    output=ToolOutput(format="text", parser="gobuster_parser", creates_assets=True),
    default_timeout=3600,
    tags=["directory", "brute-force", "web"],
))

register_tool(ToolDefinition(
    slug="ffuf",
    name="FFUF",
    description="Fast web fuzzer",
    category=ToolCategory.WEB_APPLICATION,
    version="2.1.0",
    docker_image="kali-ffuf",
    command_template="ffuf -u {url} -w {wordlist} {method} {filters} -of json",
    parameters=[
        ToolParameter(
            name="url",
            label="URL with FUZZ keyword",
            type=ParameterType.STRING,
            description="Target URL with FUZZ placeholder",
            required=True,
            placeholder="https://example.com/FUZZ",
        ),
        ToolParameter(
            name="wordlist",
            label="Wordlist",
            type=ParameterType.WORDLIST,
            description="Wordlist to use (-w)",
            default="/usr/share/wordlists/dirb/common.txt",
        ),
        ToolParameter(
            name="method",
            label="HTTP Method",
            type=ParameterType.SELECT,
            description="HTTP method to use (-X)",
            default="GET",
            options=[
                {"value": "GET", "label": "GET"},
                {"value": "POST", "label": "POST"},
                {"value": "PUT", "label": "PUT"},
                {"value": "DELETE", "label": "DELETE"},
            ],
        ),
        ToolParameter(
            name="filters",
            label="Filters",
            type=ParameterType.STRING,
            description="Response filters",
            placeholder="-fc 404 or -fs 0",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="ffuf_parser", creates_assets=True),
    default_timeout=3600,
    tags=["fuzzing", "directory", "web"],
))

register_tool(ToolDefinition(
    slug="sqlmap",
    name="SQLMap",
    description="Automatic SQL injection and database takeover tool",
    category=ToolCategory.WEB_APPLICATION,
    version="1.7.12",
    docker_image="kali-sqlmap",
    command_template="sqlmap -u {url} {data} --level {level} --risk {risk} {technique} --batch --output-dir=/tmp/sqlmap",
    parameters=[
        ToolParameter(
            name="url",
            label="Target URL",
            type=ParameterType.STRING,
            description="Target URL with parameter",
            required=True,
            placeholder="https://example.com/page.php?id=1",
        ),
        ToolParameter(
            name="data",
            label="POST Data",
            type=ParameterType.STRING,
            description="POST data string (--data)",
            placeholder="--data 'username=test&password=test'",
        ),
        ToolParameter(
            name="level",
            label="Level",
            type=ParameterType.SELECT,
            description="Level of tests to perform (1-5)",
            default="1",
            options=[
                {"value": "1", "label": "1 (Default)"},
                {"value": "2", "label": "2"},
                {"value": "3", "label": "3"},
                {"value": "4", "label": "4"},
                {"value": "5", "label": "5 (Maximum)"},
            ],
        ),
        ToolParameter(
            name="risk",
            label="Risk",
            type=ParameterType.SELECT,
            description="Risk of tests to perform (1-3)",
            default="1",
            options=[
                {"value": "1", "label": "1 (Default)"},
                {"value": "2", "label": "2"},
                {"value": "3", "label": "3 (Maximum)"},
            ],
        ),
        ToolParameter(
            name="technique",
            label="Techniques",
            type=ParameterType.STRING,
            description="SQL injection techniques to use (--technique)",
            placeholder="--technique BEUSTQ",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="text", parser="sqlmap_parser", creates_vulnerabilities=True),
    default_timeout=7200,
    tags=["sql", "injection", "database"],
))

# =============================================================================
# PASSWORD ATTACK TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="hydra",
    name="Hydra",
    description="Fast and flexible online password cracking tool",
    category=ToolCategory.PASSWORD_ATTACKS,
    version="9.5",
    docker_image="kali-hydra",
    command_template="hydra {target} {service} -L {userlist} -P {passlist} {options} -o -",
    parameters=[
        ToolParameter(
            name="target",
            label="Target",
            type=ParameterType.TARGET,
            description="Target host",
            required=True,
        ),
        ToolParameter(
            name="service",
            label="Service",
            type=ParameterType.SELECT,
            description="Service to attack",
            required=True,
            options=[
                {"value": "ssh", "label": "SSH"},
                {"value": "ftp", "label": "FTP"},
                {"value": "http-get", "label": "HTTP GET"},
                {"value": "http-post-form", "label": "HTTP POST Form"},
                {"value": "mysql", "label": "MySQL"},
                {"value": "postgres", "label": "PostgreSQL"},
                {"value": "smb", "label": "SMB"},
                {"value": "rdp", "label": "RDP"},
                {"value": "vnc", "label": "VNC"},
            ],
        ),
        ToolParameter(
            name="userlist",
            label="Username List",
            type=ParameterType.WORDLIST,
            description="File with usernames (-L)",
            default="/usr/share/wordlists/metasploit/unix_users.txt",
        ),
        ToolParameter(
            name="passlist",
            label="Password List",
            type=ParameterType.WORDLIST,
            description="File with passwords (-P)",
            default="/usr/share/wordlists/rockyou.txt",
        ),
        ToolParameter(
            name="options",
            label="Additional Options",
            type=ParameterType.STRING,
            description="Additional hydra options",
            placeholder="-t 4 -f",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="text", parser="hydra_parser", creates_vulnerabilities=True),
    default_timeout=7200,
    tags=["password", "brute-force", "online"],
))

register_tool(ToolDefinition(
    slug="john",
    name="John the Ripper",
    description="Password cracking tool",
    category=ToolCategory.PASSWORD_ATTACKS,
    version="1.9.0",
    docker_image="kali-john",
    command_template="john {hash_file} {format} {wordlist} {rules}",
    parameters=[
        ToolParameter(
            name="hash_file",
            label="Hash File",
            type=ParameterType.FILE,
            description="File containing hashes to crack",
            required=True,
        ),
        ToolParameter(
            name="format",
            label="Hash Format",
            type=ParameterType.SELECT,
            description="Hash format (--format)",
            options=[
                {"value": "--format=raw-md5", "label": "MD5"},
                {"value": "--format=raw-sha1", "label": "SHA1"},
                {"value": "--format=raw-sha256", "label": "SHA256"},
                {"value": "--format=bcrypt", "label": "bcrypt"},
                {"value": "--format=nt", "label": "NTLM"},
                {"value": "--format=lm", "label": "LM"},
            ],
        ),
        ToolParameter(
            name="wordlist",
            label="Wordlist",
            type=ParameterType.WORDLIST,
            description="Wordlist to use (--wordlist)",
            default="--wordlist=/usr/share/wordlists/rockyou.txt",
        ),
        ToolParameter(
            name="rules",
            label="Rules",
            type=ParameterType.STRING,
            description="Word mangling rules (--rules)",
            placeholder="--rules=best64",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="text", parser="john_parser"),
    default_timeout=86400,
    tags=["password", "cracking", "offline"],
))

# =============================================================================
# ADDITIONAL RECONNAISSANCE TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="amass",
    name="Amass",
    description="In-depth attack surface mapping and asset discovery",
    category=ToolCategory.RECONNAISSANCE,
    version="4.2.0",
    docker_image="kali-amass",
    command_template="amass enum -d {domain} {passive} {brute} {sources} -json -",
    parameters=[
        ToolParameter(
            name="domain",
            label="Domain",
            type=ParameterType.STRING,
            description="Target domain",
            required=True,
            placeholder="example.com",
        ),
        ToolParameter(
            name="passive",
            label="Passive Only",
            type=ParameterType.BOOLEAN,
            description="Only use passive sources (-passive)",
            default=True,
        ),
        ToolParameter(
            name="brute",
            label="Brute Force",
            type=ParameterType.BOOLEAN,
            description="Enable subdomain brute forcing (-brute)",
            default=False,
        ),
        ToolParameter(
            name="sources",
            label="Sources",
            type=ParameterType.STRING,
            description="Specific data sources to use",
            placeholder="-src crtsh,virustotal",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="amass_parser", creates_assets=True),
    default_timeout=7200,
    tags=["subdomain", "enumeration", "osint"],
))

register_tool(ToolDefinition(
    slug="whatweb",
    name="WhatWeb",
    description="Web technology fingerprinting tool",
    category=ToolCategory.RECONNAISSANCE,
    version="0.5.5",
    docker_image="kali-whatweb",
    command_template="whatweb {url} {aggression} --log-json=-",
    parameters=[
        ToolParameter(
            name="url",
            label="Target URL",
            type=ParameterType.STRING,
            description="Target URL to analyze",
            required=True,
            placeholder="https://example.com",
        ),
        ToolParameter(
            name="aggression",
            label="Aggression Level",
            type=ParameterType.SELECT,
            description="Scan aggression level (-a)",
            default="-a 1",
            options=[
                {"value": "-a 1", "label": "Stealthy", "description": "One HTTP request"},
                {"value": "-a 3", "label": "Aggressive", "description": "Multiple requests"},
                {"value": "-a 4", "label": "Heavy", "description": "Many requests"},
            ],
        ),
    ],
    output=ToolOutput(format="json", parser="whatweb_parser", creates_assets=True),
    default_timeout=600,
    tags=["fingerprint", "technology", "web"],
))

register_tool(ToolDefinition(
    slug="wpscan",
    name="WPScan",
    description="WordPress vulnerability scanner",
    category=ToolCategory.WEB_APPLICATION,
    version="3.8.25",
    docker_image="kali-wpscan",
    command_template="wpscan --url {url} {enumerate} {api_token} --format json",
    parameters=[
        ToolParameter(
            name="url",
            label="WordPress URL",
            type=ParameterType.STRING,
            description="Target WordPress URL",
            required=True,
            placeholder="https://example.com/wordpress",
        ),
        ToolParameter(
            name="enumerate",
            label="Enumerate",
            type=ParameterType.MULTI_SELECT,
            description="What to enumerate (-e)",
            options=[
                {"value": "vp", "label": "Vulnerable Plugins"},
                {"value": "ap", "label": "All Plugins"},
                {"value": "vt", "label": "Vulnerable Themes"},
                {"value": "at", "label": "All Themes"},
                {"value": "u", "label": "Users"},
                {"value": "cb", "label": "Config Backups"},
            ],
            default=["vp", "vt", "u"],
        ),
        ToolParameter(
            name="api_token",
            label="API Token",
            type=ParameterType.SECRET,
            description="WPScan API token for vulnerability data",
            placeholder="--api-token YOUR_TOKEN",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="wpscan_parser", creates_vulnerabilities=True),
    default_timeout=3600,
    tags=["wordpress", "cms", "vulnerability"],
))

register_tool(ToolDefinition(
    slug="xsstrike",
    name="XSStrike",
    description="Advanced XSS detection and exploitation suite",
    category=ToolCategory.WEB_APPLICATION,
    version="3.1.5",
    docker_image="kali-xsstrike",
    command_template="xsstrike -u {url} {data} {headers} --json",
    parameters=[
        ToolParameter(
            name="url",
            label="Target URL",
            type=ParameterType.STRING,
            description="Target URL with parameters",
            required=True,
            placeholder="https://example.com/search?q=test",
        ),
        ToolParameter(
            name="data",
            label="POST Data",
            type=ParameterType.STRING,
            description="POST data (-d)",
            placeholder="-d 'param=value'",
        ),
        ToolParameter(
            name="headers",
            label="Custom Headers",
            type=ParameterType.STRING,
            description="Custom headers (--headers)",
            placeholder="--headers 'Cookie: session=abc'",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="xsstrike_parser", creates_vulnerabilities=True),
    default_timeout=1800,
    tags=["xss", "injection", "web"],
))

register_tool(ToolDefinition(
    slug="hashcat",
    name="Hashcat",
    description="Advanced password recovery tool (GPU-accelerated)",
    category=ToolCategory.PASSWORD_ATTACKS,
    version="6.2.6",
    docker_image="kali-hashcat",
    command_template="hashcat -m {hash_type} {hash_file} {wordlist} {rules} {attack_mode} --status --status-json",
    parameters=[
        ToolParameter(
            name="hash_file",
            label="Hash File",
            type=ParameterType.FILE,
            description="File containing hashes",
            required=True,
        ),
        ToolParameter(
            name="hash_type",
            label="Hash Type",
            type=ParameterType.SELECT,
            description="Hash type mode (-m)",
            required=True,
            options=[
                {"value": "0", "label": "MD5"},
                {"value": "100", "label": "SHA1"},
                {"value": "1400", "label": "SHA256"},
                {"value": "1700", "label": "SHA512"},
                {"value": "1000", "label": "NTLM"},
                {"value": "3000", "label": "LM"},
                {"value": "3200", "label": "bcrypt"},
                {"value": "13100", "label": "Kerberos TGS-REP"},
                {"value": "18200", "label": "Kerberos AS-REP"},
            ],
        ),
        ToolParameter(
            name="wordlist",
            label="Wordlist",
            type=ParameterType.WORDLIST,
            description="Wordlist for dictionary attack",
            default="/usr/share/wordlists/rockyou.txt",
        ),
        ToolParameter(
            name="attack_mode",
            label="Attack Mode",
            type=ParameterType.SELECT,
            description="Attack mode (-a)",
            default="-a 0",
            options=[
                {"value": "-a 0", "label": "Straight (Dictionary)"},
                {"value": "-a 1", "label": "Combination"},
                {"value": "-a 3", "label": "Brute-force"},
                {"value": "-a 6", "label": "Hybrid Wordlist + Mask"},
                {"value": "-a 7", "label": "Hybrid Mask + Wordlist"},
            ],
        ),
        ToolParameter(
            name="rules",
            label="Rules",
            type=ParameterType.STRING,
            description="Rule file for word mangling (-r)",
            placeholder="-r /usr/share/hashcat/rules/best64.rule",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="json", parser="hashcat_parser"),
    default_timeout=86400,
    requires_root=True,
    tags=["password", "hash", "gpu"],
))

# =============================================================================
# NETWORK TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="netcat",
    name="Netcat",
    description="TCP/UDP network utility for reading and writing data",
    category=ToolCategory.EXPLOITATION,
    version="1.10",
    docker_image="kali-netcat",
    command_template="nc {options} {host} {port}",
    parameters=[
        ToolParameter(
            name="host",
            label="Host",
            type=ParameterType.TARGET,
            description="Target host",
            required=True,
        ),
        ToolParameter(
            name="port",
            label="Port",
            type=ParameterType.PORT,
            description="Target port",
            required=True,
        ),
        ToolParameter(
            name="options",
            label="Options",
            type=ParameterType.STRING,
            description="Netcat options",
            default="-v",
            placeholder="-v -z (scan) or -l (listen)",
        ),
    ],
    output=ToolOutput(format="text"),
    default_timeout=300,
    tags=["network", "tcp", "udp"],
))

register_tool(ToolDefinition(
    slug="dig",
    name="Dig",
    description="DNS lookup utility",
    category=ToolCategory.RECONNAISSANCE,
    version="9.18",
    docker_image="kali-dig",
    command_template="dig {domain} {record_type} {server} +noall +answer +comments",
    parameters=[
        ToolParameter(
            name="domain",
            label="Domain",
            type=ParameterType.STRING,
            description="Domain to query",
            required=True,
            placeholder="example.com",
        ),
        ToolParameter(
            name="record_type",
            label="Record Type",
            type=ParameterType.SELECT,
            description="DNS record type",
            default="ANY",
            options=[
                {"value": "ANY", "label": "Any"},
                {"value": "A", "label": "A (IPv4)"},
                {"value": "AAAA", "label": "AAAA (IPv6)"},
                {"value": "MX", "label": "MX (Mail)"},
                {"value": "NS", "label": "NS (Nameserver)"},
                {"value": "TXT", "label": "TXT"},
                {"value": "CNAME", "label": "CNAME"},
                {"value": "SOA", "label": "SOA"},
                {"value": "PTR", "label": "PTR (Reverse)"},
            ],
        ),
        ToolParameter(
            name="server",
            label="DNS Server",
            type=ParameterType.STRING,
            description="DNS server to query (@server)",
            placeholder="@8.8.8.8",
            advanced=True,
        ),
    ],
    output=ToolOutput(format="text", parser="dig_parser", creates_assets=True),
    default_timeout=60,
    tags=["dns", "lookup", "recon"],
))

register_tool(ToolDefinition(
    slug="whois",
    name="Whois",
    description="Domain registration information lookup",
    category=ToolCategory.RECONNAISSANCE,
    version="5.5",
    docker_image="kali-whois",
    command_template="whois {domain}",
    parameters=[
        ToolParameter(
            name="domain",
            label="Domain",
            type=ParameterType.STRING,
            description="Domain to lookup",
            required=True,
            placeholder="example.com",
        ),
    ],
    output=ToolOutput(format="text", parser="whois_parser"),
    default_timeout=60,
    tags=["domain", "whois", "osint"],
))

register_tool(ToolDefinition(
    slug="sslscan",
    name="SSLScan",
    description="SSL/TLS configuration scanner",
    category=ToolCategory.RECONNAISSANCE,
    version="2.0.16",
    docker_image="kali-sslscan",
    command_template="sslscan {host}:{port} --xml=-",
    parameters=[
        ToolParameter(
            name="host",
            label="Host",
            type=ParameterType.TARGET,
            description="Target host",
            required=True,
        ),
        ToolParameter(
            name="port",
            label="Port",
            type=ParameterType.PORT,
            description="Target port",
            default=443,
        ),
    ],
    output=ToolOutput(format="xml", parser="sslscan_parser", creates_vulnerabilities=True),
    default_timeout=300,
    tags=["ssl", "tls", "certificate"],
))

register_tool(ToolDefinition(
    slug="testssl",
    name="Testssl.sh",
    description="Comprehensive SSL/TLS testing tool",
    category=ToolCategory.VULNERABILITY_SCANNING,
    version="3.2",
    docker_image="kali-testssl",
    command_template="testssl.sh {url} --jsonfile=-",
    parameters=[
        ToolParameter(
            name="url",
            label="URL/Host",
            type=ParameterType.STRING,
            description="Target URL or host:port",
            required=True,
            placeholder="example.com:443",
        ),
    ],
    output=ToolOutput(format="json", parser="testssl_parser", creates_vulnerabilities=True),
    default_timeout=1800,
    tags=["ssl", "tls", "security"],
))

# =============================================================================
# EXPLOITATION TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="metasploit",
    name="Metasploit Framework",
    description="Penetration testing framework",
    category=ToolCategory.EXPLOITATION,
    version="6.3",
    docker_image="kali-metasploit",
    command_template="msfconsole -q -x '{commands}'",
    parameters=[
        ToolParameter(
            name="commands",
            label="Commands",
            type=ParameterType.TEXTAREA,
            description="Metasploit commands to execute",
            required=True,
            placeholder="use exploit/multi/handler; set PAYLOAD windows/meterpreter/reverse_tcp; set LHOST 192.168.1.100; exploit",
        ),
    ],
    output=ToolOutput(format="text"),
    default_timeout=7200,
    requires_root=True,
    tags=["exploit", "framework", "pentest"],
))

register_tool(ToolDefinition(
    slug="searchsploit",
    name="SearchSploit",
    description="Exploit-DB command line search tool",
    category=ToolCategory.EXPLOITATION,
    version="4.0",
    docker_image="kali-exploitdb",
    command_template="searchsploit {query} --json",
    parameters=[
        ToolParameter(
            name="query",
            label="Search Query",
            type=ParameterType.STRING,
            description="Search term for exploits",
            required=True,
            placeholder="apache 2.4",
        ),
    ],
    output=ToolOutput(format="json", parser="searchsploit_parser"),
    default_timeout=60,
    tags=["exploit", "search", "database"],
))

# =============================================================================
# WIRELESS TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="aircrack-ng",
    name="Aircrack-ng",
    description="WiFi security auditing tool suite",
    category=ToolCategory.WIRELESS,
    version="1.7",
    docker_image="kali-aircrack",
    command_template="aircrack-ng {capture_file} -w {wordlist}",
    parameters=[
        ToolParameter(
            name="capture_file",
            label="Capture File",
            type=ParameterType.FILE,
            description="Capture file (.cap)",
            required=True,
        ),
        ToolParameter(
            name="wordlist",
            label="Wordlist",
            type=ParameterType.WORDLIST,
            description="Wordlist for cracking",
            default="/usr/share/wordlists/rockyou.txt",
        ),
    ],
    output=ToolOutput(format="text", parser="aircrack_parser"),
    default_timeout=86400,
    requires_root=True,
    tags=["wifi", "wireless", "cracking"],
))

# =============================================================================
# SOCIAL ENGINEERING TOOLS
# =============================================================================

register_tool(ToolDefinition(
    slug="theharvester",
    name="theHarvester",
    description="OSINT tool for gathering emails, subdomains, hosts, and more",
    category=ToolCategory.SOCIAL_ENGINEERING,
    version="4.4.3",
    docker_image="kali-theharvester",
    command_template="theHarvester -d {domain} -b {sources} -f /tmp/output",
    parameters=[
        ToolParameter(
            name="domain",
            label="Domain",
            type=ParameterType.STRING,
            description="Target domain",
            required=True,
            placeholder="example.com",
        ),
        ToolParameter(
            name="sources",
            label="Data Sources",
            type=ParameterType.MULTI_SELECT,
            description="Sources to search (-b)",
            options=[
                {"value": "all", "label": "All Sources"},
                {"value": "google", "label": "Google"},
                {"value": "bing", "label": "Bing"},
                {"value": "linkedin", "label": "LinkedIn"},
                {"value": "twitter", "label": "Twitter"},
                {"value": "shodan", "label": "Shodan"},
                {"value": "hunter", "label": "Hunter.io"},
                {"value": "github-code", "label": "GitHub Code"},
            ],
            default=["all"],
        ),
    ],
    output=ToolOutput(format="json", parser="theharvester_parser", creates_assets=True),
    default_timeout=1800,
    tags=["osint", "email", "subdomain"],
))
