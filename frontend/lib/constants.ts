// Copyright 2025 milbert.ai

export const APP_NAME = 'kwebbie';
export const APP_DESCRIPTION = 'Web interface for Kali Linux security tools';

export const SEVERITY_LEVELS = ['critical', 'high', 'medium', 'low', 'info'] as const;
export type SeverityLevel = (typeof SEVERITY_LEVELS)[number];

export const SEVERITY_COLORS: Record<SeverityLevel, { bg: string; text: string; border: string }> = {
  critical: { bg: 'bg-critical', text: 'text-critical-foreground', border: 'border-critical' },
  high: { bg: 'bg-high', text: 'text-high-foreground', border: 'border-high' },
  medium: { bg: 'bg-medium', text: 'text-medium-foreground', border: 'border-medium' },
  low: { bg: 'bg-low', text: 'text-low-foreground', border: 'border-low' },
  info: { bg: 'bg-info', text: 'text-info-foreground', border: 'border-info' },
};

export const JOB_STATUSES = ['pending', 'queued', 'running', 'completed', 'failed', 'cancelled'] as const;
export type JobStatus = (typeof JOB_STATUSES)[number];

export const JOB_STATUS_COLORS: Record<JobStatus, string> = {
  pending: 'bg-yellow-500',
  queued: 'bg-blue-500',
  running: 'bg-green-500 animate-pulse',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
};

export const PROJECT_STATUSES = ['active', 'completed', 'archived'] as const;
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export const ASSET_TYPES = ['host', 'domain', 'url', 'service', 'network'] as const;
export type AssetType = (typeof ASSET_TYPES)[number];

export const ASSET_TYPE_ICONS: Record<AssetType, string> = {
  host: 'Server',
  domain: 'Globe',
  url: 'Link',
  service: 'Plug',
  network: 'Network',
};

export const VULNERABILITY_STATUSES = ['open', 'confirmed', 'false_positive', 'remediated', 'accepted'] as const;
export type VulnerabilityStatus = (typeof VULNERABILITY_STATUSES)[number];

export const TOOL_CATEGORIES = [
  { value: 'recon', label: 'Reconnaissance', description: 'Network and host discovery' },
  { value: 'vuln', label: 'Vulnerability Scanning', description: 'Vulnerability detection' },
  { value: 'web', label: 'Web Application', description: 'Web application testing' },
  { value: 'password', label: 'Password Attacks', description: 'Credential testing and cracking' },
  { value: 'exploit', label: 'Exploitation', description: 'Exploitation frameworks' },
] as const;

export const USER_ROLES = ['admin', 'manager', 'operator', 'viewer'] as const;
export type UserRole = (typeof USER_ROLES)[number];

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrator',
  manager: 'Project Manager',
  operator: 'Operator',
  viewer: 'Viewer',
};

export const REPORT_TEMPLATES = [
  { value: 'executive', label: 'Executive Summary', description: 'High-level overview for management' },
  { value: 'technical', label: 'Technical Report', description: 'Detailed technical findings' },
  { value: 'compliance', label: 'Compliance Report', description: 'OWASP/PCI-DSS compliance mapping' },
] as const;

export const REPORT_FORMATS = ['pdf', 'docx', 'html', 'md'] as const;
export type ReportFormat = (typeof REPORT_FORMATS)[number];

export const KEYBOARD_SHORTCUTS = {
  commandPalette: { key: 'k', modifier: 'meta', description: 'Open command palette' },
  search: { key: '/', modifier: null, description: 'Focus search' },
  newProject: { key: 'p', modifier: 'meta+shift', description: 'New project' },
  newJob: { key: 'j', modifier: 'meta+shift', description: 'New job' },
  toggleDarkMode: { key: 'd', modifier: 'meta+shift', description: 'Toggle dark mode' },
  escape: { key: 'Escape', modifier: null, description: 'Close modal/cancel' },
} as const;

export const PAGINATION_SIZES = [10, 25, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 25;

export const API_ROUTES = {
  auth: {
    login: '/api/v1/auth/login',
    register: '/api/v1/auth/register',
    refresh: '/api/v1/auth/refresh',
    logout: '/api/v1/auth/logout',
    me: '/api/v1/auth/me',
  },
  users: '/api/v1/users',
  projects: '/api/v1/projects',
  assets: '/api/v1/assets',
  tools: '/api/v1/tools',
  jobs: '/api/v1/jobs',
  vulnerabilities: '/api/v1/vulnerabilities',
  credentials: '/api/v1/credentials',
  workflows: '/api/v1/workflows',
  reports: '/api/v1/reports',
} as const;

export const ROUTES = {
  home: '/',
  login: '/login',
  register: '/register',
  dashboard: '/dashboard',
  projects: '/projects',
  projectDetail: (id: string) => `/projects/${id}`,
  projectAssets: (id: string) => `/projects/${id}/assets`,
  projectScans: (id: string) => `/projects/${id}/scans`,
  projectVulnerabilities: (id: string) => `/projects/${id}/vulnerabilities`,
  projectCredentials: (id: string) => `/projects/${id}/credentials`,
  projectReports: (id: string) => `/projects/${id}/reports`,
  tools: '/tools',
  toolDetail: (slug: string) => `/tools/${slug}`,
  jobs: '/jobs',
  jobDetail: (id: string) => `/jobs/${id}`,
  workflows: '/workflows',
  workflowDetail: (id: string) => `/workflows/${id}`,
  settings: '/settings',
} as const;
