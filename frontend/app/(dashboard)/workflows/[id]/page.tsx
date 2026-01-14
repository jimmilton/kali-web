'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Node, Edge } from 'reactflow';
import { ArrowLeft, Save, Play, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { WorkflowBuilder } from '@/components/workflows/workflow-builder';
import {
  useWorkflow,
  useWorkflowRuns,
  useUpdateWorkflow,
  useRunWorkflow,
} from '@/hooks/use-workflows';
import { useTools } from '@/hooks/use-tools';
import { useProjects } from '@/hooks/use-projects';
import { formatRelativeTime } from '@/lib/utils';
import Link from 'next/link';
import { WorkflowRun } from '@/lib/api';

export default function WorkflowPage() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;

  const { data: workflow, isLoading } = useWorkflow(workflowId);
  const { data: runs = [] } = useWorkflowRuns(workflowId);
  const { data: tools = [] } = useTools();
  const { projects } = useProjects();
  const updateWorkflow = useUpdateWorkflow();
  const runWorkflow = useRunWorkflow();

  const [showRunDialog, setShowRunDialog] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [activeTab, setActiveTab] = useState('editor');

  const handleSave = async (nodes: Node[], edges: Edge[]) => {
    if (!workflow) return;

    await updateWorkflow.mutateAsync({
      id: workflowId,
      data: {
        definition: {
          nodes: nodes.map((node) => ({
            id: node.id,
            type: node.type as 'tool' | 'condition' | 'delay' | 'notification',
            position: node.position,
            data: node.data,
          })),
          edges: edges.map((edge) => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            condition: edge.sourceHandle || undefined,
          })),
        },
      },
    });
  };

  const handleRun = async () => {
    if (!selectedProject) return;

    try {
      await runWorkflow.mutateAsync({
        workflowId,
        projectId: selectedProject,
      });
      setShowRunDialog(false);
      setActiveTab('runs');
    } catch {
      // Error handled by mutation
    }
  };

  if (isLoading) {
    return (
      <div className="h-[calc(100vh-4rem)] flex flex-col">
        <div className="flex items-center gap-4 p-4 border-b">
          <Skeleton className="h-8 w-8" />
          <div>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64 mt-1" />
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)]">
        <h2 className="text-xl font-semibold">Workflow not found</h2>
        <Button className="mt-4" asChild>
          <Link href="/workflows">Back to Workflows</Link>
        </Button>
      </div>
    );
  }

  const initialNodes: Node[] = workflow.definition.nodes.map((node) => ({
    id: node.id,
    type: node.type,
    position: node.position,
    data: node.data,
  }));

  const initialEdges: Edge[] = workflow.definition.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.condition,
    animated: true,
  }));

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/workflows">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">{workflow.name}</h1>
              {workflow.is_template && (
                <Badge variant="secondary">Template</Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {workflow.description || 'No description'}
            </p>
          </div>
        </div>
        <Button onClick={() => setShowRunDialog(true)}>
          <Play className="h-4 w-4 mr-2" />
          Run Workflow
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <div className="border-b px-4">
          <TabsList className="h-10">
            <TabsTrigger value="editor">Editor</TabsTrigger>
            <TabsTrigger value="runs">
              Runs
              {runs.length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {runs.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="editor" className="flex-1 m-0">
          <WorkflowBuilder
            initialNodes={initialNodes}
            initialEdges={initialEdges}
            tools={tools.map((t) => ({ slug: t.slug, name: t.name }))}
            onSave={handleSave}
          />
        </TabsContent>

        <TabsContent value="runs" className="flex-1 m-0 p-4 overflow-auto">
          {runs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <Clock className="h-12 w-12 mb-4" />
              <p>No runs yet</p>
              <Button className="mt-4" onClick={() => setShowRunDialog(true)}>
                <Play className="h-4 w-4 mr-2" />
                Run Workflow
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {runs.map((run: WorkflowRun) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-4 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <RunStatusIcon status={run.status} />
                    <div>
                      <p className="font-medium">Run #{run.id.slice(0, 8)}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatRelativeTime(run.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant={getStatusVariant(run.status)}>
                      {run.status}
                    </Badge>
                    {run.completed_at && (
                      <span className="text-sm text-muted-foreground">
                        Duration: {calculateDuration(run.started_at, run.completed_at)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={showRunDialog} onOpenChange={setShowRunDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Run Workflow</DialogTitle>
            <DialogDescription>
              Select a project to run this workflow against
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Project</Label>
              <Select value={selectedProject} onValueChange={setSelectedProject}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a project" />
                </SelectTrigger>
                <SelectContent>
                  {projects.map((project) => (
                    <SelectItem key={project.id} value={project.id}>
                      {project.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRunDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRun}
              disabled={!selectedProject || runWorkflow.isPending}
            >
              <Play className="h-4 w-4 mr-2" />
              {runWorkflow.isPending ? 'Starting...' : 'Start Run'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function RunStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'running':
      return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-500" />;
    default:
      return <Clock className="h-5 w-5 text-yellow-500" />;
  }
}

function getStatusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'completed':
      return 'default';
    case 'running':
      return 'secondary';
    case 'failed':
      return 'destructive';
    default:
      return 'outline';
  }
}

function calculateDuration(start?: string, end?: string): string {
  if (!start || !end) return '-';
  const startDate = new Date(start);
  const endDate = new Date(end);
  const seconds = Math.floor((endDate.getTime() - startDate.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}
