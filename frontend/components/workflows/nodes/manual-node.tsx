'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { UserCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ManualNodeData {
  label: string;
  prompt?: string;
  timeout?: number;
}

export const ManualNode = memo(({ data, selected }: NodeProps<ManualNodeData>) => {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[180px]',
        selected ? 'border-primary' : 'border-pink-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-pink-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-pink-500/10">
          <UserCheck className="h-4 w-4 text-pink-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Manual Approval</div>
          <div className="font-medium text-sm truncate">
            {data.prompt || data.label || 'Awaiting Approval'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-pink-500" />
    </div>
  );
});

ManualNode.displayName = 'ManualNode';
