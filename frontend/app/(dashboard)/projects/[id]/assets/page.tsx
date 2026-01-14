'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Server, Globe, Network, Plus, Search, Filter } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useProject } from '@/hooks/use-projects';

const assetTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  host: Server,
  domain: Globe,
  network: Network,
};

export default function ProjectAssetsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { project, isLoading } = useProject(projectId);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');

  // Mock assets for now - would come from API
  const assets: Array<{
    id: string;
    type: string;
    value: string;
    status: string;
    risk_score: number;
    created_at: string;
  }> = [];

  if (isLoading) {
    return <AssetsSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assets"
        description={`Discovered assets for ${project?.name || 'project'}`}
      >
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Asset
        </Button>
      </PageHeader>

      <Card>
        <CardHeader className="py-3">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search assets..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="host">Hosts</SelectItem>
                <SelectItem value="domain">Domains</SelectItem>
                <SelectItem value="network">Networks</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {assets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Server className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold">No assets found</h3>
              <p className="text-muted-foreground mt-1">
                Run a scan to discover assets or add them manually
              </p>
              <div className="flex gap-2 mt-4">
                <Button variant="outline">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Manually
                </Button>
                <Button asChild>
                  <Link href="/tools">Run Scan</Link>
                </Button>
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Discovered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assets.map((asset) => {
                  const Icon = assetTypeIcons[asset.type] || Server;
                  return (
                    <TableRow key={asset.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          <span className="capitalize">{asset.type}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono">{asset.value}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{asset.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={asset.risk_score > 70 ? 'destructive' : 'secondary'}>
                          {asset.risk_score}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(asset.created_at).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function AssetsSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
