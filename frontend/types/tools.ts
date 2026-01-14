export interface Tool {
  name: string;
  slug: string;
  description: string;
  category: ToolCategory;
  docker_image: string;
  parameters: ToolParameter[];
  output_parsers?: string[];
  documentation_url?: string;
  version?: string;
}

export type ToolCategory = 'recon' | 'vuln' | 'web' | 'password' | 'exploit';

export interface ToolParameter {
  name: string;
  type: ParameterType;
  label: string;
  description?: string;
  required: boolean;
  default?: unknown;
  options?: ParameterOption[];
  validation?: ParameterValidation;
  placeholder?: string;
  group?: string;
  depends_on?: ParameterDependency;
}

export type ParameterType =
  | 'string'
  | 'number'
  | 'integer'
  | 'float'
  | 'boolean'
  | 'select'
  | 'multiselect'
  | 'multi_select'
  | 'file'
  | 'target'
  | 'port'
  | 'port_range'
  | 'ip'
  | 'domain'
  | 'url'
  | 'wordlist'
  | 'textarea'
  | 'secret';

export interface ParameterOption {
  label: string;
  value: string;
  description?: string;
}

export interface ParameterValidation {
  pattern?: string;
  min?: number;
  max?: number;
  min_length?: number;
  max_length?: number;
  allowed_extensions?: string[];
  max_file_size?: number;
}

export interface ParameterDependency {
  parameter: string;
  value: unknown;
  operator?: 'equals' | 'not_equals' | 'contains' | 'exists';
}

export interface ToolExecution {
  tool: Tool;
  parameters: Record<string, unknown>;
  targets: string[];
  command_preview?: string;
}

export interface ToolResult {
  tool_name: string;
  status: 'success' | 'partial' | 'failed';
  execution_time: number;
  findings_count: number;
  raw_output?: string;
  parsed_data?: ParsedToolResult;
}

export interface ParsedToolResult {
  type: string;
  items: ParsedResultItem[];
  summary?: Record<string, unknown>;
}

export interface ParsedResultItem {
  id: string;
  type: string;
  data: Record<string, unknown>;
  severity?: string;
  confidence?: string;
}

// Tool-specific result types
export interface NmapResult {
  hosts: NmapHost[];
  scan_info: {
    start_time: string;
    end_time: string;
    args: string;
  };
}

export interface NmapHost {
  ip: string;
  hostname?: string;
  status: 'up' | 'down';
  ports: NmapPort[];
  os?: {
    name: string;
    accuracy: number;
  };
}

export interface NmapPort {
  number: number;
  protocol: 'tcp' | 'udp';
  state: 'open' | 'closed' | 'filtered';
  service?: {
    name: string;
    product?: string;
    version?: string;
  };
  scripts?: Record<string, string>;
}

export interface NucleiResult {
  findings: NucleiFinding[];
  stats: {
    total: number;
    matched: number;
    templates_loaded: number;
  };
}

export interface NucleiFinding {
  template_id: string;
  template_name: string;
  severity: string;
  host: string;
  matched_at: string;
  extracted_results?: string[];
  curl_command?: string;
  description?: string;
  reference?: string[];
  tags?: string[];
}

export interface GobusterResult {
  entries: GobusterEntry[];
  stats: {
    requests: number;
    errors: number;
    duration: number;
  };
}

export interface GobusterEntry {
  url: string;
  status: number;
  size: number;
  redirect?: string;
}

export interface HydraResult {
  credentials: HydraCredential[];
  stats: {
    attempts: number;
    success: number;
    failed: number;
  };
}

export interface HydraCredential {
  host: string;
  port: number;
  service: string;
  username: string;
  password: string;
}

// Tool categories with metadata
export const TOOL_CATEGORIES: Record<ToolCategory, ToolCategoryInfo> = {
  recon: {
    name: 'Reconnaissance',
    description: 'Network and host discovery tools',
    icon: 'Search',
    color: 'blue',
  },
  vuln: {
    name: 'Vulnerability Scanning',
    description: 'Vulnerability detection and assessment',
    icon: 'ShieldAlert',
    color: 'orange',
  },
  web: {
    name: 'Web Application',
    description: 'Web application testing and analysis',
    icon: 'Globe',
    color: 'purple',
  },
  password: {
    name: 'Password Attacks',
    description: 'Credential testing and cracking',
    icon: 'Key',
    color: 'red',
  },
  exploit: {
    name: 'Exploitation',
    description: 'Exploitation frameworks and tools',
    icon: 'Zap',
    color: 'yellow',
  },
};

export interface ToolCategoryInfo {
  name: string;
  description: string;
  icon: string;
  color: string;
}
