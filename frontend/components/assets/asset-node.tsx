'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import {
  Server,
  Globe,
  Link,
  Network,
  Shield,
  Cpu,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AssetNodeData {
  label: string;
  asset_type: string;
  status: string;
  risk_score: number;
  metadata?: Record<string, unknown>;
}

const typeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  host: Server,
  domain: Globe,
  subdomain: Globe,
  url: Link,
  service: Cpu,
  network: Network,
  endpoint: Link,
  certificate: Shield,
  technology: Cpu,
};

const typeColors: Record<string, string> = {
  host: 'bg-green-500/10 border-green-500 text-green-500',
  domain: 'bg-blue-500/10 border-blue-500 text-blue-500',
  subdomain: 'bg-purple-500/10 border-purple-500 text-purple-500',
  url: 'bg-orange-500/10 border-orange-500 text-orange-500',
  service: 'bg-cyan-500/10 border-cyan-500 text-cyan-500',
  network: 'bg-yellow-500/10 border-yellow-500 text-yellow-500',
  endpoint: 'bg-pink-500/10 border-pink-500 text-pink-500',
  certificate: 'bg-indigo-500/10 border-indigo-500 text-indigo-500',
  technology: 'bg-teal-500/10 border-teal-500 text-teal-500',
};

export const AssetNode = memo(({ data, selected }: NodeProps<AssetNodeData>) => {
  const Icon = typeIcons[data.asset_type] || Server;
  const colorClasses = typeColors[data.asset_type] || 'bg-gray-500/10 border-gray-500 text-gray-500';

  const getRiskColor = (score: number) => {
    if (score >= 80) return 'text-red-500';
    if (score >= 60) return 'text-orange-500';
    if (score >= 40) return 'text-yellow-500';
    return 'text-green-500';
  };

  return (
    <div
      className={cn(
        'px-3 py-2 rounded-lg border-2 bg-background shadow-md min-w-[140px] max-w-[200px]',
        colorClasses,
        selected && 'ring-2 ring-primary ring-offset-2'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-current" />

      <div className="flex items-start gap-2">
        <Icon className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-muted-foreground uppercase">
            {data.asset_type}
          </div>
          <div className="font-medium text-sm truncate text-foreground" title={data.label}>
            {data.label}
          </div>
        </div>
      </div>

      {data.risk_score > 0 && (
        <div className={cn('flex items-center gap-1 mt-1 text-xs', getRiskColor(data.risk_score))}>
          <AlertTriangle className="h-3 w-3" />
          Risk: {data.risk_score}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-current" />
    </div>
  );
});

AssetNode.displayName = 'AssetNode';
