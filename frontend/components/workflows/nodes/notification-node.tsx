'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Bell } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NotificationNodeData {
  label: string;
  message?: string;
  type?: 'info' | 'success' | 'warning' | 'error';
}

export const NotificationNode = memo(({ data, selected }: NodeProps<NotificationNodeData>) => {
  return (
    <div
      className={cn(
        'px-4 py-3 rounded-lg border-2 bg-background shadow-md min-w-[150px]',
        selected ? 'border-primary' : 'border-purple-500'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-purple-500" />
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded bg-purple-500/10">
          <Bell className="h-4 w-4 text-purple-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground">Notification</div>
          <div className="font-medium text-sm truncate">
            {data.message || data.label || 'Set Message'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-purple-500" />
    </div>
  );
});

NotificationNode.displayName = 'NotificationNode';
