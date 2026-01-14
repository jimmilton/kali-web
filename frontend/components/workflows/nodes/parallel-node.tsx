'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { GitFork } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ParallelNodeData {
  label: string;
  branches?: number;
}

export const ParallelNode = memo(({ data, selected }: NodeProps<ParallelNodeData>) => {
  const branches = data.branches || 2;

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[180px]',
        selected ? 'border-primary' : 'border-orange-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-orange-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-orange-500/10">
          <GitFork className="h-4 w-4 text-orange-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Parallel</div>
          <div className="font-medium text-sm truncate">
            {data.label || `${branches} Branches`}
          </div>
        </div>
      </div>
      {[...Array(branches)].map((_, i) => (
        <Handle
          key={i}
          type="source"
          position={Position.Bottom}
          id={`branch-${i}`}
          className="!bg-orange-500"
          style={{ left: `${((i + 1) / (branches + 1)) * 100}%` }}
        />
      ))}
    </div>
  );
});

ParallelNode.displayName = 'ParallelNode';
