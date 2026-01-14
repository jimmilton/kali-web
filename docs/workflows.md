# Workflow Automation Guide

Copyright 2025 milbert.ai

Workflows allow you to automate multi-step security testing processes with conditional logic, parallel execution, and manual approval gates.

## Workflow Concepts

### Nodes

Workflows are built from connected nodes:

| Node Type | Description | Example |
|-----------|-------------|---------|
| **Tool** | Execute a security tool | Run Nmap scan |
| **Condition** | Branch based on results | If ports found > 10 |
| **Parallel** | Run multiple nodes simultaneously | Scan multiple targets |
| **Loop** | Iterate over a list | Scan each subdomain |
| **Delay** | Wait for specified time | Wait 60 seconds |
| **Manual** | Require user approval | Approve before exploit |
| **Notification** | Send alerts | Notify on completion |

### Context Variables

Workflows maintain a context that stores:
- Input parameters
- Node results
- Loop iteration data

Access variables using `${variable}` syntax:
```
${target}                    # Input parameter
${node_1_result.exit_code}   # Previous node result
${loop_item}                 # Current loop item
${loop_index}                # Current loop index
```

## Building Workflows

### Visual Builder

1. **Add Nodes**: Drag from the sidebar onto the canvas
2. **Connect Nodes**: Click and drag from one node's handle to another
3. **Configure Nodes**: Click a node to open its properties panel
4. **Save**: Click Save to persist the workflow

### Node Configuration

#### Tool Node

```json
{
  "type": "tool",
  "tool_slug": "nmap",
  "parameters": {
    "target": "${target}",
    "ports": "-p 1-1000"
  }
}
```

#### Condition Node

```json
{
  "type": "condition",
  "condition": "node_1_result.exit_code == 0",
  "true_branch": "node_2",
  "false_branch": "node_3"
}
```

Supported operators:
- `==`, `!=` - Equality
- `>`, `<`, `>=`, `<=` - Comparison
- `contains` - Check if list contains value

#### Parallel Node

```json
{
  "type": "parallel",
  "children": ["node_2", "node_3", "node_4"]
}
```

#### Loop Node

```json
{
  "type": "loop",
  "items": "${discovered_subdomains}",
  "item_variable": "subdomain",
  "children": ["scan_node"]
}
```

Inside the loop, access:
- `${loop_item}` - Current item
- `${loop_index}` - Current index (0-based)
- `${loop_total}` - Total items

#### Delay Node

```json
{
  "type": "delay",
  "seconds": 60
}
```

#### Manual Node

```json
{
  "type": "manual",
  "message": "Review findings before continuing",
  "timeout_seconds": 3600
}
```

#### Notification Node

```json
{
  "type": "notification",
  "message": "Scan complete: ${node_1_result.hosts_found} hosts found",
  "channel": "websocket"
}
```

## Example Workflows

### Basic Reconnaissance

```
[Subfinder] --> [HTTPX] --> [Nuclei]
```

1. Discover subdomains
2. Probe for live hosts
3. Scan for vulnerabilities

### Conditional Scanning

```
[Nmap] --> [Condition: ports > 0?]
                |
        +-------+-------+
        |               |
    [Nuclei]        [Notify: No ports]
```

### Parallel Scanning

```
            +---> [Nmap] --+
            |              |
[Start] --> + ---> [SSL] --+--> [Report]
            |              |
            +---> [HTTP] --+
```

### Full Security Audit

```
[Subfinder] --> [HTTPX] --> [Parallel]
                               |
                    +----------+----------+
                    |          |          |
                [Nuclei]  [Nikto]   [SSLScan]
                    |          |          |
                    +----------+----------+
                               |
                           [Manual: Review]
                               |
                           [Report]
```

## Executing Workflows

### Via UI

1. Navigate to **Workflows**
2. Click on a workflow
3. Click **Execute**
4. Enter parameters
5. Select target project
6. Click **Run**

### Via API

```bash
POST /api/v1/workflows/{id}/execute
{
  "project_id": "uuid",
  "parameters": {
    "target": "example.com"
  }
}
```

## Monitoring Execution

### Workflow Run Status

- **Pending**: Waiting to start
- **Running**: Currently executing
- **Waiting Approval**: Paused at manual node
- **Completed**: Successfully finished
- **Failed**: Error occurred
- **Cancelled**: User cancelled

### Real-time Updates

WebSocket events notify you of:
- `workflow_started`
- `workflow_node_started`
- `workflow_node_completed`
- `workflow_approval_required`
- `workflow_completed`
- `workflow_failed`

## Manual Approval

When a workflow reaches a manual node:

1. Workflow pauses with status `WAITING_APPROVAL`
2. WebSocket event notifies connected clients
3. Review the results so far
4. Approve or reject via UI or API:

```bash
POST /api/v1/workflows/runs/{run_id}/approve
{
  "approved": true,
  "notes": "Findings look legitimate, proceeding"
}
```

## Best Practices

1. **Start Simple**: Begin with linear workflows before adding conditions
2. **Use Delays**: Add delays between scans to avoid rate limiting
3. **Manual Gates**: Add manual approval before destructive actions
4. **Test Parameters**: Use test targets before running on production
5. **Monitor Results**: Watch job outputs during execution
6. **Handle Errors**: Plan for tool failures with conditions
