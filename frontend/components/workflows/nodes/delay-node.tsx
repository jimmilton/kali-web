'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DelayNodeData {
  label: string;
  duration?: number;
  unit?: 'seconds' | 'minutes' | 'hours';
}

export const DelayNode = memo(({ data, selected }: NodeProps<DelayNodeData>) => {
  const displayDuration = data.duration
    ? `${data.duration} ${data.unit || 'seconds'}`
    : 'Set Duration';

  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[150px]',
        selected ? 'border-primary' : 'border-blue-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-blue-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-blue-500/10">
          <Clock className="h-4 w-4 text-blue-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Delay</div>
          <div className="font-medium text-sm truncate">{displayDuration}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-blue-500" />
    </div>
  );
});

DelayNode.displayName = 'DelayNode';
