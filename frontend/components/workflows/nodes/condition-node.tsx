'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConditionNodeData {
  label: string;
  condition?: string;
}

export const ConditionNode = memo(({ data, selected }: NodeProps<ConditionNodeData>) => {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[180px]',
        selected ? 'border-primary' : 'border-yellow-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-yellow-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-yellow-500/10">
          <GitBranch className="h-4 w-4 text-yellow-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Condition</div>
          <div className="font-medium text-sm truncate">
            {data.condition || data.label || 'Set Condition'}
          </div>
        </div>
      </div>
      <div className="flex justify-between mt-2 text-xs text-muted-foreground">
        <span>True</span>
        <span>False</span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        className="!bg-green-500 !left-[25%]"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        className="!bg-red-500 !left-[75%]"
      />
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';
