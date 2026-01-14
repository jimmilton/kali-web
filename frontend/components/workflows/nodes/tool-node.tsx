'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ToolNodeData {
  label: string;
  tool?: string;
  parameters?: Record<string, unknown>;
}

export const ToolNode = memo(({ data, selected }: NodeProps<ToolNodeData>) => {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[180px]',
        selected ? 'border-primary' : 'border-green-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-green-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-green-500/10">
          <Wrench className="h-4 w-4 text-green-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Tool</div>
          <div className="font-medium text-sm truncate">
            {data.tool || data.label || 'Select Tool'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-green-500" />
    </div>
  );
});

ToolNode.displayName = 'ToolNode';
