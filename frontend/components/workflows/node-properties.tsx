'use client';

import { useEffect, useState } from 'react';
import { Node } from 'reactflow';
import {
  Wrench,
  GitBranch,
  Clock,
  Bell,
  GitFork,
  Repeat,
  UserCheck,
  X,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

interface NodePropertiesProps {
  node: Node | null;
  tools: Array<{ slug: string; name: string }>;
  onUpdate: (nodeId: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

const nodeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  tool: Wrench,
  condition: GitBranch,
  delay: Clock,
  notification: Bell,
  parallel: GitFork,
  loop: Repeat,
  manual: UserCheck,
};

const nodeColors: Record<string, string> = {
  tool: 'text-green-500',
  condition: 'text-yellow-500',
  delay: 'text-blue-500',
  notification: 'text-purple-500',
  parallel: 'text-orange-500',
  loop: 'text-cyan-500',
  manual: 'text-pink-500',
};

export function NodeProperties({ node, tools, onUpdate, onClose }: NodePropertiesProps) {
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (node) {
      setFormData(node.data);
    }
  }, [node]);

  if (!node) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full text-muted-foreground">
          Select a node to edit its properties
        </CardContent>
      </Card>
    );
  }

  const nodeType = node.type || 'tool';
  const Icon = nodeIcons[nodeType] || Wrench;
  const color = nodeColors[nodeType] || 'text-gray-500';

  const handleChange = (key: string, value: unknown) => {
    const newData = { ...formData, [key]: value };
    setFormData(newData);
    onUpdate(node.id, newData);
  };

  return (
    <Card className="h-full">
      <CardHeader className="py-3 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={cn('h-4 w-4', color)} />
          <CardTitle className="text-sm capitalize">{node.type} Properties</CardTitle>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Label</Label>
          <Input
            value={(formData.label as string) || ''}
            onChange={(e) => handleChange('label', e.target.value)}
            placeholder="Node label"
          />
        </div>

        {node.type === 'tool' && (
          <>
            <div className="space-y-2">
              <Label>Tool</Label>
              <Select
                value={(formData.tool as string) || ''}
                onValueChange={(value) => handleChange('tool', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a tool" />
                </SelectTrigger>
                <SelectContent>
                  {tools.map((tool) => (
                    <SelectItem key={tool.slug} value={tool.slug}>
                      {tool.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Parameters (JSON)</Label>
              <Textarea
                value={JSON.stringify(formData.parameters || {}, null, 2)}
                onChange={(e) => {
                  try {
                    handleChange('parameters', JSON.parse(e.target.value));
                  } catch {
                    // Invalid JSON, don't update
                  }
                }}
                placeholder="{}"
                rows={4}
                className="font-mono text-sm"
              />
            </div>
          </>
        )}

        {node.type === 'condition' && (
          <div className="space-y-2">
            <Label>Condition</Label>
            <Input
              value={(formData.condition as string) || ''}
              onChange={(e) => handleChange('condition', e.target.value)}
              placeholder="e.g., status == completed"
            />
            <p className="text-xs text-muted-foreground">
              Use: ==, !=, {'>'}, {'<'}, {'>='}', {'<='}, contains
            </p>
          </div>
        )}

        {node.type === 'delay' && (
          <>
            <div className="space-y-2">
              <Label>Duration</Label>
              <Input
                type="number"
                min={1}
                value={(formData.duration as number) || ''}
                onChange={(e) => handleChange('duration', parseInt(e.target.value))}
                placeholder="Duration"
              />
            </div>
            <div className="space-y-2">
              <Label>Unit</Label>
              <Select
                value={(formData.unit as string) || 'seconds'}
                onValueChange={(value) => handleChange('unit', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="seconds">Seconds</SelectItem>
                  <SelectItem value="minutes">Minutes</SelectItem>
                  <SelectItem value="hours">Hours</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        )}

        {node.type === 'notification' && (
          <>
            <div className="space-y-2">
              <Label>Message</Label>
              <Textarea
                value={(formData.message as string) || ''}
                onChange={(e) => handleChange('message', e.target.value)}
                placeholder="Notification message"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={(formData.type as string) || 'info'}
                onValueChange={(value) => handleChange('type', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="warning">Warning</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        )}

        {node.type === 'parallel' && (
          <div className="space-y-2">
            <Label>Number of Branches</Label>
            <Input
              type="number"
              min={2}
              max={5}
              value={(formData.branches as number) || 2}
              onChange={(e) => handleChange('branches', parseInt(e.target.value))}
            />
          </div>
        )}

        {node.type === 'loop' && (
          <>
            <div className="space-y-2">
              <Label>Iterations</Label>
              <Input
                type="number"
                min={1}
                value={(formData.iterations as number) || ''}
                onChange={(e) => handleChange('iterations', parseInt(e.target.value))}
                placeholder="Number of iterations"
              />
            </div>
            <div className="space-y-2">
              <Label>Variable Name</Label>
              <Input
                value={(formData.variable as string) || ''}
                onChange={(e) => handleChange('variable', e.target.value)}
                placeholder="e.g., item"
              />
            </div>
          </>
        )}

        {node.type === 'manual' && (
          <>
            <div className="space-y-2">
              <Label>Approval Prompt</Label>
              <Textarea
                value={(formData.prompt as string) || ''}
                onChange={(e) => handleChange('prompt', e.target.value)}
                placeholder="Message to show when requesting approval"
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>Timeout (minutes)</Label>
              <Input
                type="number"
                min={1}
                value={(formData.timeout as number) || ''}
                onChange={(e) => handleChange('timeout', parseInt(e.target.value))}
                placeholder="Optional timeout"
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
