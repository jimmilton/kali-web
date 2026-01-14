'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2, Network, AlertTriangle, Server, Info } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { AssetGraph } from '@/components/assets/asset-graph';
import { assetsApi, AssetGraph as AssetGraphType } from '@/lib/api';

export default function ProjectGraphPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const { data: graphData, isLoading, error } = useQuery({
    queryKey: ['asset-graph', projectId],
    queryFn: () => assetsApi.getGraph(projectId),
  });

  const selectedAsset = graphData?.nodes.find((n) => n.id === selectedAssetId);

  if (isLoading) {
    return (
      <div className="h-[calc(100vh-4rem)] flex flex-col">
        <div className="flex items-center gap-4 p-4 border-b">
          <Skeleton className="h-8 w-8" />
          <div>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64 mt-1" />
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[calc(100vh-4rem)] flex flex-col items-center justify-center">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold">Failed to load graph</h2>
        <p className="text-muted-foreground mt-2">Could not load asset relationship data</p>
        <Button className="mt-4" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  const hasNodes = graphData && graphData.nodes.length > 0;

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/projects/${projectId}`}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5 text-primary" />
              <h1 className="text-xl font-semibold">Asset Relationship Graph</h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Visualize how assets are connected to each other
            </p>
          </div>
        </div>
        {graphData && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{graphData.nodes.length} assets</span>
            <span>{graphData.edges.length} relationships</span>
          </div>
        )}
      </div>

      {/* Graph or Empty State */}
      {hasNodes ? (
        <div className="flex-1">
          <AssetGraph
            nodes={graphData.nodes}
            edges={graphData.edges}
            onNodeClick={(nodeId) => setSelectedAssetId(nodeId)}
          />
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <Card className="max-w-md">
            <CardHeader className="text-center">
              <div className="mx-auto p-3 rounded-full bg-muted w-fit mb-2">
                <Server className="h-8 w-8 text-muted-foreground" />
              </div>
              <CardTitle>No Assets Yet</CardTitle>
              <CardDescription>
                Run scans to discover assets and their relationships
              </CardDescription>
            </CardHeader>
            <CardContent className="text-center">
              <Button asChild>
                <Link href={`/projects/${projectId}/scans`}>Run a Scan</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Asset Details Sheet */}
      <Sheet open={!!selectedAssetId} onOpenChange={() => setSelectedAssetId(null)}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Asset Details
            </SheetTitle>
            <SheetDescription>
              Information about the selected asset
            </SheetDescription>
          </SheetHeader>

          {selectedAsset && (
            <div className="mt-6 space-y-4">
              <div>
                <label className="text-xs text-muted-foreground uppercase">Type</label>
                <Badge variant="outline" className="mt-1 block w-fit">
                  {selectedAsset.data.asset_type}
                </Badge>
              </div>

              <div>
                <label className="text-xs text-muted-foreground uppercase">Value</label>
                <p className="font-mono text-sm mt-1 break-all">
                  {selectedAsset.data.label}
                </p>
              </div>

              <div>
                <label className="text-xs text-muted-foreground uppercase">Status</label>
                <Badge
                  variant={selectedAsset.data.status === 'active' ? 'default' : 'secondary'}
                  className="mt-1 block w-fit"
                >
                  {selectedAsset.data.status}
                </Badge>
              </div>

              <div>
                <label className="text-xs text-muted-foreground uppercase">Risk Score</label>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full ${
                        selectedAsset.data.risk_score >= 80
                          ? 'bg-red-500'
                          : selectedAsset.data.risk_score >= 60
                          ? 'bg-orange-500'
                          : selectedAsset.data.risk_score >= 40
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                      style={{ width: `${selectedAsset.data.risk_score}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{selectedAsset.data.risk_score}</span>
                </div>
              </div>

              {selectedAsset.data.metadata && Object.keys(selectedAsset.data.metadata).length > 0 && (
                <div>
                  <label className="text-xs text-muted-foreground uppercase">Metadata</label>
                  <pre className="mt-1 p-2 rounded bg-muted text-xs overflow-auto max-h-48">
                    {JSON.stringify(selectedAsset.data.metadata, null, 2)}
                  </pre>
                </div>
              )}

              <div className="pt-4">
                <Button variant="outline" className="w-full" asChild>
                  <Link href={`/projects/${projectId}/assets?id=${selectedAssetId}`}>
                    View Full Details
                  </Link>
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Legend */}
      <div className="border-t p-2 flex items-center gap-4 text-xs">
        <span className="text-muted-foreground flex items-center gap-1">
          <Info className="h-3 w-3" />
          Legend:
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-green-500" /> Host
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-blue-500" /> Domain
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-purple-500" /> Subdomain
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-orange-500" /> URL
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-cyan-500" /> Service
        </span>
      </div>
    </div>
  );
}
