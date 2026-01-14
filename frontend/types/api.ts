// API Response types
export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
}

export interface ApiError {
  detail: string;
  status: number;
  code?: string;
  errors?: ValidationError[];
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

// Create/Update input types
export interface CreateProjectInput {
  name: string;
  description?: string;
  scope?: {
    domains?: string[];
    ips?: string[];
    exclude?: string[];
  };
  settings?: Record<string, unknown>;
}

export interface UpdateProjectInput extends Partial<CreateProjectInput> {}

export interface CreateAssetInput {
  type: string;
  value: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
}

export interface UpdateAssetInput extends Partial<CreateAssetInput> {}

export interface ImportAssetsInput {
  assets: CreateAssetInput[];
}

export interface ImportAssetsResponse {
  imported: number;
  skipped: number;
  errors?: string[];
}

export interface CreateJobInput {
  project_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  target_ids?: string[];
  priority?: number;
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

export interface UpdateVulnerabilityInput extends Partial<CreateVulnerabilityInput> {
  status?: string;
  assigned_to?: string;
}

export interface CreateCredentialInput {
  asset_id?: string;
  username?: string;
  password?: string;
  hash?: string;
  hash_type?: string;
  source?: string;
}

export interface CreateWorkflowInput {
  project_id?: string;
  name: string;
  description?: string;
  definition: {
    nodes: WorkflowNodeInput[];
    edges: WorkflowEdgeInput[];
  };
  is_template?: boolean;
}

export interface WorkflowNodeInput {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface WorkflowEdgeInput {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface UpdateWorkflowInput extends Partial<CreateWorkflowInput> {}

export interface RunWorkflowInput {
  project_id: string;
}

export interface CreateReportInput {
  title: string;
  template?: string;
  content?: Record<string, unknown>;
  format: string;
}

export interface UpdateReportInput extends Partial<CreateReportInput> {}

export interface CreateNoteInput {
  project_id: string;
  asset_id?: string;
  vulnerability_id?: string;
  content: string;
}

export interface UpdateNoteInput {
  content: string;
}

// Filter types
export interface ProjectFilters extends PaginationParams {
  status?: string;
  search?: string;
}

export interface AssetFilters extends PaginationParams {
  type?: string;
  tags?: string[];
  search?: string;
}

export interface JobFilters extends PaginationParams {
  project_id?: string;
  status?: string;
  tool_name?: string;
}

export interface VulnerabilityFilters extends PaginationParams {
  severity?: string;
  status?: string;
  asset_id?: string;
  search?: string;
}

export interface CredentialFilters extends PaginationParams {
  asset_id?: string;
  hash_type?: string;
  is_valid?: boolean;
}

export interface WorkflowFilters extends PaginationParams {
  project_id?: string;
  is_template?: boolean;
}

export interface AuditLogFilters extends PaginationParams {
  user_id?: string;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

// Tool API types
export interface ToolPreviewRequest {
  parameters: Record<string, unknown>;
}

export interface ToolPreviewResponse {
  command: string;
}

export interface ToolListParams {
  category?: string;
}

// Stats types
export interface DashboardStats {
  projects: {
    total: number;
    active: number;
  };
  assets: {
    total: number;
    by_type: Record<string, number>;
  };
  vulnerabilities: {
    total: number;
    by_severity: Record<string, number>;
    open: number;
  };
  jobs: {
    total: number;
    running: number;
    completed_today: number;
  };
}

export interface TimelineEntry {
  id: string;
  type: 'job' | 'vulnerability' | 'asset' | 'report';
  action: string;
  title: string;
  description?: string;
  timestamp: string;
  user?: {
    id: string;
    username: string;
  };
  metadata?: Record<string, unknown>;
}
