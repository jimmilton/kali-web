'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Repeat } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoopNodeData {
  label: string;
  iterations?: number;
  variable?: string;
}

export const LoopNode = memo(({ data, selected }: NodeProps<LoopNodeData>) => {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[150px]',
        selected ? 'border-primary' : 'border-cyan-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-cyan-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-cyan-500/10">
          <Repeat className="h-4 w-4 text-cyan-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Loop</div>
          <div className="font-medium text-sm truncate">
            {data.iterations ? `${data.iterations}x` : data.label || 'Configure Loop'}
          </div>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        id="body"
        className="!bg-cyan-500 !left-[25%]"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="exit"
        className="!bg-gray-500 !left-[75%]"
      />
      <Handle
        type="target"
        position={Position.Left}
        id="loop-back"
        className="!bg-cyan-500"
      />
    </div>
  );
});

LoopNode.displayName = 'LoopNode';
