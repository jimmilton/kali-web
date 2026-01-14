'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Node, Edge } from 'reactflow';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { WorkflowBuilder } from '@/components/workflows/workflow-builder';
import { useCreateWorkflow } from '@/hooks/use-workflows';
import { useTools } from '@/hooks/use-tools';
import Link from 'next/link';

export default function NewWorkflowPage() {
  const router = useRouter();
  const { data: tools = [] } = useTools();
  const createWorkflow = useCreateWorkflow();

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isTemplate, setIsTemplate] = useState(false);

  const handleSave = (newNodes: Node[], newEdges: Edge[]) => {
    setNodes(newNodes);
    setEdges(newEdges);
    setShowSaveDialog(true);
  };

  const handleCreate = async () => {
    if (!name.trim()) return;

    try {
      const workflow = await createWorkflow.mutateAsync({
        name,
        description: description || undefined,
        is_template: isTemplate,
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
      });
      router.push(`/workflows/${workflow.id}`);
    } catch {
      // Error handled by mutation
    }
  };

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
            <h1 className="text-xl font-semibold">Create Workflow</h1>
            <p className="text-sm text-muted-foreground">
              Drag and drop nodes to build your workflow
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1">
        <WorkflowBuilder
          tools={tools.map((t) => ({ slug: t.slug, name: t.name }))}
          onSave={handleSave}
        />
      </div>

      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Workflow</DialogTitle>
            <DialogDescription>
              Enter a name and description for your workflow
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Workflow"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this workflow does..."
                rows={3}
              />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Template</Label>
                <p className="text-sm text-muted-foreground">
                  Make this a reusable template
                </p>
              </div>
              <Switch checked={isTemplate} onCheckedChange={setIsTemplate} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!name.trim() || createWorkflow.isPending}
            >
              <Save className="h-4 w-4 mr-2" />
              {createWorkflow.isPending ? 'Creating...' : 'Create Workflow'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
