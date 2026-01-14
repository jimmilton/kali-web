'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface AssetChartProps {
  byType: Record<string, number>;
  total: number;
}

const TYPE_COLORS: Record<string, string> = {
  host: '#3b82f6',
  domain: '#8b5cf6',
  url: '#06b6d4',
  service: '#10b981',
  network: '#f59e0b',
  endpoint: '#ec4899',
  database: '#6366f1',
  credential: '#ef4444',
  other: '#6b7280',
};

export function AssetChart({ byType, total }: AssetChartProps) {
  const chartData = useMemo(() => {
    return Object.entries(byType)
      .map(([type, count]) => ({
        type: type.charAt(0).toUpperCase() + type.slice(1),
        count,
        color: TYPE_COLORS[type] || TYPE_COLORS.other,
      }))
      .sort((a, b) => b.count - a.count);
  }, [byType]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assets</CardTitle>
        <CardDescription>
          {total} total assets by type
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[250px]">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                <XAxis type="number" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis
                  type="category"
                  dataKey="type"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--popover))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              No assets found
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
