// User types
export interface User {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type UserRole = 'admin' | 'manager' | 'operator' | 'viewer';

// Project types
export interface Project {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  scope?: ProjectScope;
  settings?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
  members?: ProjectMember[];
}

export type ProjectStatus = 'active' | 'completed' | 'archived';

export interface ProjectScope {
  domains?: string[];
  ips?: string[];
  exclude?: string[];
}

export interface ProjectMember {
  project_id: string;
  user_id: string;
  role: ProjectRole;
  user?: User;
}

export type ProjectRole = 'owner' | 'manager' | 'member' | 'viewer';

export interface ProjectStats {
  assets: number;
  vulnerabilities: VulnerabilitySeverityCount;
  jobs: JobStatusCount;
}

export interface VulnerabilitySeverityCount {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface JobStatusCount {
  running: number;
  completed: number;
  failed: number;
}

// Asset types
export interface Asset {
  id: string;
  project_id: string;
  type: AssetType;
  value: string;
  metadata?: Record<string, unknown>;
  tags?: string[];
  risk_score: number;
  status: string;
  discovered_by?: string;
  created_at: string;
  updated_at: string;
}

export type AssetType = 'host' | 'domain' | 'url' | 'service' | 'network';

export interface AssetRelation {
  parent_id: string;
  child_id: string;
  relation_type: string;
}

// Job types
export interface Job {
  id: string;
  project_id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  command?: string;
  status: JobStatus;
  priority: number;
  container_id?: string;
  exit_code?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_by: string;
  created_at: string;
  targets?: Asset[];
}

export type JobStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface JobOutput {
  id: string;
  job_id: string;
  output_type: 'stdout' | 'stderr' | 'system';
  content: string;
  timestamp: string;
}

// Result types
export interface Result {
  id: string;
  job_id: string;
  asset_id?: string;
  result_type: string;
  raw_data?: string;
  parsed_data?: Record<string, unknown>;
  severity?: Severity;
  created_at: string;
}

// Vulnerability types
export interface Vulnerability {
  id: string;
  project_id: string;
  asset_id?: string;
  title: string;
  description?: string;
  severity: Severity;
  cvss_score?: number;
  cve_ids?: string[];
  cwe_ids?: string[];
  evidence?: string;
  proof_of_concept?: string;
  remediation?: string;
  references?: string[];
  status: VulnerabilityStatus;
  discovered_by?: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
  asset?: Asset;
}

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type VulnerabilityStatus = 'open' | 'confirmed' | 'false_positive' | 'remediated' | 'accepted';

export interface VulnerabilityStats {
  total: number;
  by_severity: VulnerabilitySeverityCount;
  by_status: Record<VulnerabilityStatus, number>;
}

// Credential types
export interface Credential {
  id: string;
  project_id: string;
  asset_id?: string;
  username?: string;
  hash_type?: string;
  source?: string;
  is_valid?: boolean;
  discovered_by?: string;
  created_at: string;
  asset?: Asset;
}

// Workflow types
export interface Workflow {
  id: string;
  project_id?: string;
  name: string;
  description?: string;
  definition: WorkflowDefinition;
  is_template: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export type WorkflowNodeType = 'tool' | 'condition' | 'delay' | 'notification';

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  project_id: string;
  status: WorkflowRunStatus;
  current_step: number;
  context: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  created_by: string;
  created_at: string;
}

export type WorkflowRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

// Report types
export interface Report {
  id: string;
  project_id: string;
  title: string;
  template?: ReportTemplate;
  content?: Record<string, unknown>;
  format: ReportFormat;
  file_path?: string;
  generated_at?: string;
  created_by: string;
  created_at: string;
}

export type ReportTemplate = 'executive' | 'technical' | 'compliance';

export type ReportFormat = 'pdf' | 'docx' | 'html' | 'md';

// Note types
export interface Note {
  id: string;
  project_id: string;
  asset_id?: string;
  vulnerability_id?: string;
  content: string;
  author_id: string;
  created_at: string;
  updated_at: string;
  author?: User;
}

// Audit log types
export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  details?: Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
  user?: User;
}
