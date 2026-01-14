import { getAccessToken, removeTokens } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiError {
  detail: string;
  status: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    removeTokens();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw { detail: error.detail || 'Request failed', status: response.status };
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  return handleResponse<T>(response);
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),

  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};

// MFA types
export interface MFASetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

// Auth endpoints
export const authApi = {
  login: (username: string, password: string, mfa_code?: string) =>
    api.post<{ access_token: string; refresh_token: string; token_type: string }>(
      '/api/v1/auth/login',
      { username, password, mfa_code }
    ),

  register: (data: { email: string; username: string; password: string; confirm_password: string }) =>
    api.post<{ access_token: string; refresh_token: string; token_type: string }>(
      '/api/v1/auth/register',
      data
    ),

  refresh: (refreshToken: string) =>
    api.post<{ access_token: string; refresh_token: string; token_type: string }>(
      '/api/v1/auth/refresh',
      { refresh_token: refreshToken }
    ),

  logout: (refreshToken: string) =>
    api.post<void>('/api/v1/auth/logout', { refresh_token: refreshToken }),

  me: () => api.get<User>('/api/v1/auth/me'),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<{ message: string }>('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  // MFA endpoints
  mfaSetup: () => api.post<MFASetupResponse>('/api/v1/auth/mfa/setup'),

  mfaEnable: (code: string) =>
    api.post<{ message: string }>('/api/v1/auth/mfa/enable', { code }),

  mfaDisable: (code: string) =>
    api.post<{ message: string }>('/api/v1/auth/mfa/disable', { code }),
};

// User endpoints
export const usersApi = {
  list: (params?: { page?: number; page_size?: number }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<User>>(`/api/v1/users?${query}`);
  },

  get: (id: string) => api.get<User>(`/api/v1/users/${id}`),

  update: (id: string, data: Partial<User>) =>
    api.patch<User>(`/api/v1/users/${id}`, data),

  delete: (id: string) => api.delete<void>(`/api/v1/users/${id}`),
};

// Project endpoints
export const projectsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<Project>>(`/api/v1/projects?${query}`);
  },

  get: (id: string) => api.get<Project>(`/api/v1/projects/${id}`),

  create: (data: CreateProjectInput) =>
    api.post<Project>('/api/v1/projects', data),

  update: (id: string, data: Partial<CreateProjectInput>) =>
    api.patch<Project>(`/api/v1/projects/${id}`, data),

  delete: (id: string) => api.delete<void>(`/api/v1/projects/${id}`),

  getStats: (id: string) => api.get<ProjectStats>(`/api/v1/projects/${id}/stats`),

  addMember: (projectId: string, userId: string, role: string) =>
    api.post<void>(`/api/v1/projects/${projectId}/members`, { user_id: userId, role }),

  removeMember: (projectId: string, userId: string) =>
    api.delete<void>(`/api/v1/projects/${projectId}/members/${userId}`),
};

// Asset endpoints
export const assetsApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number; type?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<Asset>>(`/api/v1/projects/${projectId}/assets?${query}`);
  },

  get: (projectId: string, id: string) =>
    api.get<Asset>(`/api/v1/projects/${projectId}/assets/${id}`),

  create: (projectId: string, data: CreateAssetInput) =>
    api.post<Asset>(`/api/v1/projects/${projectId}/assets`, data),

  update: (projectId: string, id: string, data: Partial<CreateAssetInput>) =>
    api.patch<Asset>(`/api/v1/projects/${projectId}/assets/${id}`, data),

  delete: (projectId: string, id: string) =>
    api.delete<void>(`/api/v1/projects/${projectId}/assets/${id}`),

  import: (projectId: string, data: { assets: CreateAssetInput[] }) =>
    api.post<{ imported: number; skipped: number }>(`/api/v1/projects/${projectId}/assets/import`, data),

  getGraph: (projectId: string) =>
    api.get<AssetGraph>(`/api/v1/assets/graph?project_id=${projectId}`),

  createRelation: (data: AssetRelationCreate) =>
    api.post<AssetRelation>('/api/v1/assets/relations', data),

  deleteRelation: (parentId: string, childId: string) =>
    api.delete<void>(`/api/v1/assets/relations/${parentId}/${childId}`),
};

export interface AssetGraph {
  nodes: Array<{
    id: string;
    type: string;
    data: {
      label: string;
      asset_type: string;
      status: string;
      risk_score: number;
      metadata?: Record<string, unknown>;
    };
    position: { x: number; y: number };
    style?: Record<string, unknown>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
    animated?: boolean;
  }>;
}

export interface AssetRelation {
  parent_id: string;
  child_id: string;
  relation_type: string;
  parent_value?: string;
  child_value?: string;
}

export interface AssetRelationCreate {
  parent_id: string;
  child_id: string;
  relation_type: 'has_service' | 'resolves_to' | 'belongs_to' | 'hosts' | 'uses' | 'redirects_to';
  metadata?: Record<string, unknown>;
}

// Tool endpoints
export const toolsApi = {
  list: async (params?: { category?: string }): Promise<Tool[]> => {
    const query = params?.category ? `?category=${params.category}` : '';
    const response = await api.get<{ tools: Tool[]; categories: unknown[] }>(`/api/v1/tools${query}`);
    return response.tools || [];
  },

  get: (slug: string) => api.get<Tool>(`/api/v1/tools/${slug}`),

  preview: (slug: string, parameters: Record<string, unknown>) =>
    api.post<{ command: string }>(`/api/v1/tools/${slug}/preview`, { parameters }),
};

// Job endpoints
export const jobsApi = {
  list: (params?: { page?: number; page_size?: number; project_id?: string; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<Job>>(`/api/v1/jobs?${query}`);
  },

  get: (id: string) => api.get<Job>(`/api/v1/jobs/${id}`),

  create: (data: CreateJobInput) => api.post<Job>('/api/v1/jobs', data),

  cancel: (id: string) => api.post<Job>(`/api/v1/jobs/${id}/cancel`),

  retry: (id: string) => api.post<Job>(`/api/v1/jobs/${id}/retry`),

  getOutput: (id: string) => api.get<JobOutput[]>(`/api/v1/jobs/${id}/output`),
};

// Vulnerability endpoints
export const vulnerabilitiesApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number; severity?: string; status?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<Vulnerability>>(
      `/api/v1/projects/${projectId}/vulnerabilities?${query}`
    );
  },

  get: (projectId: string, id: string) =>
    api.get<Vulnerability>(`/api/v1/projects/${projectId}/vulnerabilities/${id}`),

  create: (projectId: string, data: CreateVulnerabilityInput) =>
    api.post<Vulnerability>(`/api/v1/projects/${projectId}/vulnerabilities`, data),

  update: (projectId: string, id: string, data: Partial<CreateVulnerabilityInput>) =>
    api.patch<Vulnerability>(`/api/v1/projects/${projectId}/vulnerabilities/${id}`, data),

  delete: (projectId: string, id: string) =>
    api.delete<void>(`/api/v1/projects/${projectId}/vulnerabilities/${id}`),

  getStats: (projectId: string) =>
    api.get<VulnerabilityStats>(`/api/v1/projects/${projectId}/vulnerabilities/stats`),
};

// Credential endpoints
export const credentialsApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<Credential>>(
      `/api/v1/projects/${projectId}/credentials?${query}`
    );
  },

  get: (projectId: string, id: string) =>
    api.get<Credential>(`/api/v1/projects/${projectId}/credentials/${id}`),

  create: (projectId: string, data: CreateCredentialInput) =>
    api.post<Credential>(`/api/v1/projects/${projectId}/credentials`, data),

  delete: (projectId: string, id: string) =>
    api.delete<void>(`/api/v1/projects/${projectId}/credentials/${id}`),

  getSecret: (projectId: string, id: string) =>
    api.get<{ plaintext: string }>(`/api/v1/projects/${projectId}/credentials/${id}/secret`),
};

// Workflow endpoints
export const workflowsApi = {
  list: (params?: { page?: number; page_size?: number; project_id?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<PaginatedResponse<Workflow>>(`/api/v1/workflows?${query}`);
  },

  get: (id: string) => api.get<Workflow>(`/api/v1/workflows/${id}`),

  create: (data: CreateWorkflowInput) =>
    api.post<Workflow>('/api/v1/workflows', data),

  update: (id: string, data: Partial<CreateWorkflowInput>) =>
    api.patch<Workflow>(`/api/v1/workflows/${id}`, data),

  delete: (id: string) => api.delete<void>(`/api/v1/workflows/${id}`),

  run: (id: string, projectId: string) =>
    api.post<WorkflowRun>(`/api/v1/workflows/${id}/run`, { project_id: projectId }),

  getRuns: (id: string) =>
    api.get<WorkflowRun[]>(`/api/v1/workflows/${id}/runs`),
};

// Note: reportsApi is defined after Report types below

// Types
export interface User {
  id: string;
  email: string;
  username: string;
  role: 'admin' | 'manager' | 'operator' | 'viewer';
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'completed' | 'archived';
  scope?: {
    domains?: string[];
    ips?: string[];
    exclude?: string[];
  };
  settings?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectInput {
  name: string;
  description?: string;
  scope?: {
    domains?: string[];
    ips?: string[];
    exclude?: string[];
  };
}

export interface ProjectStats {
  assets: number;
  vulnerabilities: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  jobs: {
    running: number;
    completed: number;
    failed: number;
  };
}

export interface Asset {
  id: string;
  project_id: string;
  type: 'host' | 'domain' | 'url' | 'service' | 'network';
  value: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
  risk_score: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAssetInput {
  type: string;
  value: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
}

export interface Tool {
  name: string;
  slug: string;
  description: string;
  category: string;
  docker_image: string;
  parameters: ToolParameter[];
  output_parsers?: string[];
}

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiselect' | 'file' | 'target' | 'textarea' | 'port' | 'port_range' | 'wordlist' | 'secret' | 'integer' | 'float' | 'multi_select';
  label: string;
  description?: string;
  required: boolean;
  default?: unknown;
  options?: { label: string; value: string; description?: string }[];
  validation?: {
    pattern?: string;
    min?: number;
    max?: number;
  };
  placeholder?: string;
  group?: string;
  advanced?: boolean;
}

export interface Job {
  id: string;
  project_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  command?: string;
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  priority: number;
  exit_code?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_by: string;
  created_at: string;
}

export interface CreateJobInput {
  project_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  target_ids?: string[];
  priority?: number;
}

export interface JobOutput {
  id: string;
  job_id: string;
  output_type: 'stdout' | 'stderr' | 'system';
  content: string;
  timestamp: string;
}

export interface Vulnerability {
  id: string;
  project_id: string;
  asset_id?: string;
  title: string;
  description?: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  cvss_score?: number;
  cve_ids?: string[];
  cwe_ids?: string[];
  evidence?: string;
  proof_of_concept?: string;
  remediation?: string;
  references?: string[];
  status: 'open' | 'confirmed' | 'false_positive' | 'remediated' | 'accepted';
  discovered_by?: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateVulnerabilityInput {
  asset_id?: string;
  title: string;
  description?: string;
  severity: string;
  cvss_score?: number;
  cve_ids?: string[];
  cwe_ids?: string[];
  evidence?: string;
  proof_of_concept?: string;
  remediation?: string;
  references?: string[];
}

export interface VulnerabilityStats {
  total: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  by_status: {
    open: number;
    confirmed: number;
    false_positive: number;
    remediated: number;
    accepted: number;
  };
}

export interface Credential {
  id: string;
  project_id: string;
  asset_id?: string;
  username?: string;
  hash_type?: string;
  source?: string;
  is_valid?: boolean;
  created_at: string;
}

export interface CreateCredentialInput {
  asset_id?: string;
  username?: string;
  password?: string;
  hash?: string;
  hash_type?: string;
  source?: string;
}

export interface Workflow {
  id: string;
  project_id?: string;
  name: string;
  description?: string;
  definition: {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  };
  is_template: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowNode {
  id: string;
  type: 'tool' | 'condition' | 'delay' | 'notification';
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface CreateWorkflowInput {
  project_id?: string;
  name: string;
  description?: string;
  definition: {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  };
  is_template?: boolean;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  project_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  current_step: number;
  context: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface Report {
  id: string;
  project_id: string;
  title: string;
  template?: string;
  content?: Record<string, unknown>;
  format: 'pdf' | 'docx' | 'html' | 'md';
  file_path?: string;
  generated_at?: string;
  created_by: string;
  created_at: string;
}

export interface CreateReportInput {
  title: string;
  template?: string;
  content?: Record<string, unknown>;
  format: string;
}

// Analytics types
export interface DashboardStats {
  projects: number;
  assets: number;
  vulnerabilities: number;
  credentials: number;
  jobs_completed: number;
  jobs_running: number;
  jobs_failed: number;
}

export interface VulnerabilitySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  total: number;
}

export interface TrendDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  asset_count: number;
  vulnerability_count: number;
  last_activity: string | null;
}

export interface AnalyticsDashboard {
  stats: DashboardStats;
  vulnerability_summary: VulnerabilitySummary;
  vulnerability_trends: TrendDataPoint[];
  asset_trends: TrendDataPoint[];
  job_trends: TrendDataPoint[];
  recent_projects: ProjectSummary[];
  vulnerability_by_status: Record<string, number>;
  asset_by_type: Record<string, number>;
  top_vulnerabilities: Array<{
    id: string;
    title: string;
    severity: string;
    status: string;
    cvss_score: number | null;
    asset: string | null;
    created_at: string;
  }>;
}

// Analytics API
export const analyticsApi = {
  getDashboard: (params?: { project_id?: string; days?: number }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<AnalyticsDashboard>(`/api/v1/analytics/dashboard?${query}`);
  },

  getVulnerabilityStats: (projectId?: string) => {
    const query = projectId ? `?project_id=${projectId}` : '';
    return api.get<{
      by_severity: Record<string, number>;
      by_status: Record<string, number>;
      by_tool: Record<string, number>;
      cvss_distribution: Record<string, number>;
    }>(`/api/v1/analytics/vulnerability-stats${query}`);
  },

  getAssetStats: (projectId?: string) => {
    const query = projectId ? `?project_id=${projectId}` : '';
    return api.get<{
      by_type: Record<string, number>;
      by_status: Record<string, number>;
      risk_distribution: Record<string, number>;
      top_risky_assets: Array<{
        id: string;
        value: string;
        type: string;
        vulnerability_count: number;
      }>;
    }>(`/api/v1/analytics/asset-stats${query}`);
  },

  getJobStats: (params?: { project_id?: string; days?: number }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return api.get<{
      by_status: Record<string, number>;
      by_tool: Record<string, number>;
      avg_duration_by_tool: Record<string, number>;
      daily_trend: Array<{ date: string; count: number }>;
    }>(`/api/v1/analytics/job-stats?${query}`);
  },
};

// Import types
export interface ImportFormat {
  id: string;
  name: string;
  extensions: string[];
  description: string;
}

export interface ImportResult {
  success: boolean;
  format: string;
  assets_created: number;
  assets_updated: number;
  vulnerabilities_created: number;
  vulnerabilities_updated: number;
  credentials_created: number;
  credentials_updated: number;
  errors: string[];
}

// Import API
export const importApi = {
  getFormats: () => api.get<{ formats: ImportFormat[] }>('/api/v1/import/formats'),

  importFile: async (
    format: string,
    projectId: string,
    file: File
  ): Promise<ImportResult> => {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/import/${format}?project_id=${projectId}`,
      {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Import failed' }));
      throw { detail: error.detail || 'Import failed', status: response.status };
    }

    return response.json();
  },
};

// Report types
export type ReportTemplateType = 'executive' | 'technical' | 'compliance' | 'vulnerability' | 'asset' | 'custom';
export type ReportFormatType = 'pdf' | 'docx' | 'html' | 'markdown' | 'json';
export type ReportStatusType = 'pending' | 'generating' | 'completed' | 'failed';

export interface ReportTemplateInfo {
  id: ReportTemplateType;
  name: string;
  description: string;
  sections: string[];
}

export interface ReportBranding {
  company_name?: string;
  logo_url?: string;
  primary_color?: string;
  secondary_color?: string;
  footer_text?: string;
  header_text?: string;
}

export interface ReportContent {
  sections?: string[];
  include_evidence?: boolean;
  include_raw_output?: boolean;
  include_remediation?: boolean;
  include_references?: boolean;
  severity_filter?: string[];
  status_filter?: string[];
  vulnerability_ids?: string[];
  asset_ids?: string[];
}

export interface Report {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  template: ReportTemplateType;
  format: ReportFormatType;
  content: ReportContent;
  branding: ReportBranding;
  status: ReportStatusType;
  error_message?: string;
  file_path?: string;
  file_size?: number;
  file_hash?: string;
  generated_at?: string;
  scheduled_at?: string;
  cron_expression?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateReportInput {
  project_id: string;
  title: string;
  description?: string;
  template: ReportTemplateType;
  format: ReportFormatType;
  content?: ReportContent;
  branding?: ReportBranding;
  scheduled_at?: string;
  cron_expression?: string;
}

// Reports API
export const reportsApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number }) => {
    const queryParams = new URLSearchParams();
    queryParams.set('project_id', projectId);
    if (params?.page) queryParams.set('page', String(params.page));
    if (params?.page_size) queryParams.set('page_size', String(params.page_size));
    return api.get<PaginatedResponse<Report>>(`/api/v1/reports?${queryParams.toString()}`);
  },

  get: (id: string) => api.get<Report>(`/api/v1/reports/${id}`),

  create: (data: CreateReportInput) => api.post<Report>('/api/v1/reports', data),

  generate: (id: string) => api.post<{ message: string; success: boolean }>(`/api/v1/reports/${id}/generate`),

  delete: (id: string) => api.delete<{ message: string; success: boolean }>(`/api/v1/reports/${id}`),

  getDownloadInfo: (id: string) =>
    api.get<{
      download_url: string;
      filename: string;
      content_type: string;
      file_size: number;
      expires_at: string;
    }>(`/api/v1/reports/${id}/download`),

  download: async (id: string): Promise<Blob> => {
    const token = getAccessToken();
    const response = await fetch(`${API_BASE_URL}/api/v1/reports/${id}/stream`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      throw new Error('Failed to download report');
    }

    return response.blob();
  },

  getTemplates: () =>
    api.get<ReportTemplateInfo[]>('/api/v1/reports/templates/list'),
};

// Integration types
export interface Integration {
  id: string;
  name: string;
  type: 'slack' | 'discord' | 'jira';
  enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateIntegrationInput {
  name: string;
  type: 'slack' | 'discord' | 'jira';
  config: {
    webhook_url?: string;
    base_url?: string;
    email?: string;
    api_token?: string;
    project_key?: string;
  };
}

// Integrations API (uses settings endpoint pattern)
export const integrationsApi = {
  list: () => api.get<Integration[]>('/api/v1/integrations'),

  create: (data: CreateIntegrationInput) =>
    api.post<Integration>('/api/v1/integrations', data),

  update: (id: string, data: Partial<CreateIntegrationInput>) =>
    api.patch<Integration>(`/api/v1/integrations/${id}`, data),

  delete: (id: string) => api.delete<void>(`/api/v1/integrations/${id}`),

  test: (id: string) =>
    api.post<{ success: boolean; message: string }>(`/api/v1/integrations/${id}/test`),
};
