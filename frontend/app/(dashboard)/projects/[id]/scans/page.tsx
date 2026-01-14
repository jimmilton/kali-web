'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Terminal,
  Filter,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useProject } from '@/hooks/use-projects';
import { useJobs } from '@/hooks/use-jobs';
import { formatRelativeTime } from '@/lib/utils';

const statusConfig: Record<string, { icon: typeof Clock; label: string; variant: 'default' | 'secondary' | 'success' | 'destructive'; animate?: boolean }> = {
  pending: { icon: Clock, label: 'Pending', variant: 'secondary' },
  queued: { icon: Clock, label: 'Queued', variant: 'secondary' },
  running: { icon: Loader2, label: 'Running', variant: 'default', animate: true },
  completed: { icon: CheckCircle2, label: 'Completed', variant: 'success' },
  failed: { icon: XCircle, label: 'Failed', variant: 'destructive' },
  cancelled: { icon: XCircle, label: 'Cancelled', variant: 'secondary' },
};

export default function ProjectScansPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const { project, isLoading: projectLoading } = useProject(projectId);
  const { jobs, isLoading: jobsLoading } = useJobs({ projectId });

  const isLoading = projectLoading || jobsLoading;

  const filteredJobs = statusFilter
    ? jobs.filter(job => job.status === statusFilter)
    : jobs;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h2 className="text-xl font-semibold">Project not found</h2>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scans"
        description={`Scan jobs for ${project.name}`}
      />

      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button
            variant={statusFilter === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(null)}
          >
            All ({jobs.length})
          </Button>
          {Object.entries(statusConfig).map(([status, config]) => {
            const count = jobs.filter(j => j.status === status).length;
            if (count === 0) return null;
            return (
              <Button
                key={status}
                variant={statusFilter === status ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter(status)}
              >
                {config.label} ({count})
              </Button>
            );
          })}
        </div>
        <Button asChild>
          <Link href="/tools">
            <Play className="mr-2 h-4 w-4" />
            New Scan
          </Link>
        </Button>
      </div>

      {filteredJobs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Terminal className="h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 text-lg font-semibold">No scans yet</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Run a tool to start scanning
            </p>
            <Button className="mt-4" asChild>
              <Link href="/tools">Browse Tools</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredJobs.map((job) => {
            const config = statusConfig[job.status as keyof typeof statusConfig];
            const Icon = config?.icon || Clock;

            return (
              <Card key={job.id} className="card-hover">
                <Link href={`/jobs/${job.id}`}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                          <Terminal className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{job.tool_name}</CardTitle>
                          <CardDescription>
                            Started {formatRelativeTime(job.created_at)}
                          </CardDescription>
                        </div>
                      </div>
                      <Badge variant={config?.variant || 'secondary'}>
                        <Icon className={`mr-1 h-3 w-3 ${config?.animate ? 'animate-spin' : ''}`} />
                        {config?.label || job.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-muted-foreground font-mono truncate">
                      {job.command || 'Command preview not available'}
                    </div>
                  </CardContent>
                </Link>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
