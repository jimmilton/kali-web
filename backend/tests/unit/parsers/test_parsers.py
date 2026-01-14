"""Tests for tool output parsers."""

import pytest
from unittest.mock import MagicMock

from app.tools.parsers import get_parser
from app.tools.parsers.base import ParseOutput
from app.tools.parsers.nmap_parser import NmapParser
from app.tools.parsers.nuclei_parser import NucleiParser
from app.tools.parsers.subfinder_parser import SubfinderParser
from app.tools.parsers.masscan_parser import MasscanParser
from app.tools.parsers.httpx_parser import HttpxParser
from app.tools.parsers.gobuster_parser import GobusterParser
from app.tools.parsers.ffuf_parser import FfufParser
from app.tools.parsers.nikto_parser import NiktoParser
from app.tools.parsers.hydra_parser import HydraParser


@pytest.fixture
def mock_job():
    """Create a mock job for testing."""
    job = MagicMock()
    job.project_id = "test-project-id"
    job.parameters = {}
    return job


class TestParserRegistry:
    """Test parser registry functions."""

    def test_get_nmap_parser(self):
        parser = get_parser("nmap_parser")
        assert parser is not None
        assert isinstance(parser, NmapParser)

    def test_get_nuclei_parser(self):
        parser = get_parser("nuclei_parser")
        assert parser is not None
        assert isinstance(parser, NucleiParser)

    def test_get_nonexistent_parser(self):
        parser = get_parser("nonexistent_parser")
        assert parser is None


class TestNmapParser:
    """Test Nmap XML parser."""

    def test_parse_basic_host(self, mock_job):
        parser = NmapParser()
        xml = '''<?xml version="1.0"?>
        <nmaprun>
          <host>
            <status state="up"/>
            <address addr="192.168.1.1" addrtype="ipv4"/>
            <hostnames>
              <hostname name="server.local" type="PTR"/>
            </hostnames>
            <ports>
              <port protocol="tcp" portid="22">
                <state state="open"/>
                <service name="ssh" product="OpenSSH" version="8.2"/>
              </port>
              <port protocol="tcp" portid="80">
                <state state="open"/>
                <service name="http" product="nginx"/>
              </port>
            </ports>
          </host>
        </nmaprun>'''

        result = parser.parse(xml, mock_job)

        assert isinstance(result, ParseOutput)
        assert len(result.errors) == 0
        assert len(result.assets) >= 3  # host + domain + services
        assert len(result.results) >= 2  # port results

        # Check host asset
        host_assets = [a for a in result.assets if a.value == "192.168.1.1"]
        assert len(host_assets) == 1
        assert host_assets[0].type == "host"

    def test_parse_vulnerability_script(self, mock_job):
        parser = NmapParser()
        xml = '''<?xml version="1.0"?>
        <nmaprun>
          <host>
            <status state="up"/>
            <address addr="192.168.1.1" addrtype="ipv4"/>
            <ports>
              <port protocol="tcp" portid="445">
                <state state="open"/>
                <service name="microsoft-ds"/>
                <script id="smb-vuln-ms17-010" output="VULNERABLE: MS17-010"/>
              </port>
            </ports>
          </host>
        </nmaprun>'''

        result = parser.parse(xml, mock_job)

        assert len(result.vulnerabilities) >= 1
        vuln = result.vulnerabilities[0]
        assert "ms17-010" in vuln.title.lower() or "smb" in vuln.title.lower()
        assert vuln.severity in ["critical", "high"]

    def test_parse_invalid_xml(self, mock_job):
        parser = NmapParser()
        result = parser.parse("not valid xml", mock_job)

        assert len(result.errors) > 0


class TestNucleiParser:
    """Test Nuclei JSON parser."""

    def test_parse_json_lines(self, mock_job):
        parser = NucleiParser()
        output = '''{"template-id":"cve-2021-44228","info":{"name":"Log4j RCE","severity":"critical"},"host":"http://example.com","matched-at":"http://example.com/api"}
{"template-id":"http-missing-security-headers","info":{"name":"Missing X-Frame-Options","severity":"info"},"host":"http://example.com"}'''

        result = parser.parse(output, mock_job)

        assert len(result.vulnerabilities) == 2
        assert any("log4j" in v.title.lower() for v in result.vulnerabilities)

    def test_parse_empty_output(self, mock_job):
        parser = NucleiParser()
        result = parser.parse("", mock_job)

        assert len(result.vulnerabilities) == 0
        assert len(result.errors) == 0


class TestSubfinderParser:
    """Test Subfinder JSON parser."""

    def test_parse_subdomains(self, mock_job):
        parser = SubfinderParser()
        output = '''{"host":"api.example.com","source":"crtsh"}
{"host":"www.example.com","source":"dnsdumpster"}
{"host":"mail.example.com","source":"hackertarget"}'''

        result = parser.parse(output, mock_job)

        assert len(result.assets) == 3
        values = [a.value for a in result.assets]
        assert "api.example.com" in values
        assert "www.example.com" in values


class TestMasscanParser:
    """Test Masscan JSON parser."""

    def test_parse_hosts_and_ports(self, mock_job):
        parser = MasscanParser()
        output = '''[
            {"ip": "192.168.1.1", "ports": [{"port": 80, "proto": "tcp", "status": "open"}]},
            {"ip": "192.168.1.2", "ports": [{"port": 22, "proto": "tcp", "status": "open"}, {"port": 443, "proto": "tcp", "status": "open"}]}
        ]'''

        result = parser.parse(output, mock_job)

        assert len(result.assets) >= 2
        assert len(result.results) >= 3


class TestHttpxParser:
    """Test HTTPX JSON parser."""

    def test_parse_urls(self, mock_job):
        parser = HttpxParser()
        output = '''{"url":"https://example.com","status_code":200,"title":"Example","webserver":"nginx"}
{"url":"https://api.example.com","status_code":200,"title":"API"}'''

        result = parser.parse(output, mock_job)

        assert len(result.assets) >= 2


class TestGobusterParser:
    """Test Gobuster text parser."""

    def test_parse_directories(self, mock_job):
        parser = GobusterParser()
        output = '''/admin                (Status: 200) [Size: 1234]
/api                  (Status: 301) [Size: 0] [--> /api/]
/login                (Status: 200) [Size: 5678]'''

        result = parser.parse(output, mock_job)

        assert len(result.assets) == 3
        assert len(result.results) == 3

    def test_parse_with_base_url(self, mock_job):
        mock_job.parameters = {"url": "http://example.com"}
        parser = GobusterParser()
        output = '''/admin                (Status: 200) [Size: 1234]'''

        result = parser.parse(output, mock_job)

        assert result.assets[0].value == "http://example.com/admin"


class TestFfufParser:
    """Test FFUF JSON parser."""

    def test_parse_results(self, mock_job):
        parser = FfufParser()
        output = '''{"results":[
            {"url":"http://example.com/admin","status":200,"length":1234},
            {"url":"http://example.com/api","status":301,"length":0}
        ]}'''

        result = parser.parse(output, mock_job)

        assert len(result.assets) >= 2


class TestNiktoParser:
    """Test Nikto JSON parser."""

    def test_parse_vulnerabilities(self, mock_job):
        parser = NiktoParser()
        output = '''{"host":"example.com","ip":"93.184.216.34","port":"80","vulnerabilities":[
            {"id":"999990","method":"GET","url":"/","msg":"Server leaks inodes via ETags"},
            {"id":"999991","method":"GET","url":"/admin","msg":"Admin page found"}
        ]}'''

        result = parser.parse(output, mock_job)

        assert len(result.assets) >= 1
        assert len(result.vulnerabilities) == 2


class TestHydraParser:
    """Test Hydra text parser."""

    def test_parse_credentials(self, mock_job):
        parser = HydraParser()
        output = '''[22][ssh] host: 192.168.1.1   login: admin   password: password123
[22][ssh] host: 192.168.1.1   login: root   password: toor'''

        result = parser.parse(output, mock_job)

        assert len(result.credentials) == 2
        assert result.credentials[0].username == "admin"
        assert result.credentials[0].password == "password123"
        assert result.credentials[0].service == "ssh"
        assert result.credentials[0].port == 22
