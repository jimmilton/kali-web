'use client';

import { DragEvent } from 'react';
import {
  Wrench,
  GitBranch,
  Clock,
  Bell,
  GitFork,
  Repeat,
  UserCheck,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface NodeType {
  type: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const nodeTypes: NodeType[] = [
  {
    type: 'tool',
    label: 'Tool',
    description: 'Execute a security tool',
    icon: Wrench,
    color: 'text-green-500',
  },
  {
    type: 'condition',
    label: 'Condition',
    description: 'Branch based on condition',
    icon: GitBranch,
    color: 'text-yellow-500',
  },
  {
    type: 'delay',
    label: 'Delay',
    description: 'Wait for a duration',
    icon: Clock,
    color: 'text-blue-500',
  },
  {
    type: 'notification',
    label: 'Notification',
    description: 'Send a notification',
    icon: Bell,
    color: 'text-purple-500',
  },
  {
    type: 'parallel',
    label: 'Parallel',
    description: 'Execute branches in parallel',
    icon: GitFork,
    color: 'text-orange-500',
  },
  {
    type: 'loop',
    label: 'Loop',
    description: 'Repeat a set of steps',
    icon: Repeat,
    color: 'text-cyan-500',
  },
  {
    type: 'manual',
    label: 'Manual Approval',
    description: 'Wait for user approval',
    icon: UserCheck,
    color: 'text-pink-500',
  },
];

interface NodeSidebarProps {
  className?: string;
}

export function NodeSidebar({ className }: NodeSidebarProps) {
  const onDragStart = (event: DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Card className={cn('h-full', className)}>
      <CardHeader className="py-3">
        <CardTitle className="text-sm">Node Types</CardTitle>
      </CardHeader>
      <CardContent className="p-2 space-y-1">
        {nodeTypes.map((node) => (
          <div
            key={node.type}
            className="flex items-center gap-2 p-2 rounded-md border cursor-grab hover:bg-accent transition-colors"
            draggable
            onDragStart={(e) => onDragStart(e, node.type)}
          >
            <node.icon className={cn('h-4 w-4', node.color)} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">{node.label}</div>
              <div className="text-xs text-muted-foreground truncate">
                {node.description}
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
