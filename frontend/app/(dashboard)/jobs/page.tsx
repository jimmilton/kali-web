'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Terminal,
  Clock,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Square,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/breadcrumbs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useJobs } from '@/hooks/use-jobs';
import { formatDate, formatDuration } from '@/lib/utils';

const statusOptions = [
  { value: 'all', label: 'All Status' },
  { value: 'pending', label: 'Pending' },
  { value: 'queued', label: 'Queued' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);

  const { jobs, isLoading, pagination, refetch } = useJobs({
    status: statusFilter === 'all' ? undefined : statusFilter,
    page,
    pageSize: 25,
    autoRefresh: true,
    refreshInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Monitor and manage tool execution jobs"
      >
        <Button variant="outline" onClick={refetch}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </PageHeader>

      {/* Filters */}
      <Card>
        <CardHeader className="py-3">
          <div className="flex items-center gap-4">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
      </Card>

      {/* Jobs Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading && jobs.length === 0 ? (
            <JobsTableSkeleton />
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Terminal className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold">No jobs found</h3>
              <p className="text-muted-foreground mt-1">
                Run a tool from the Tools page to create a job
              </p>
              <Button className="mt-4" asChild>
                <Link href="/tools">Browse Tools</Link>
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tool</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Exit Code</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Terminal className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{job.tool_name}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <JobStatusBadge status={job.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(job.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {job.started_at && job.completed_at
                        ? formatDuration(
                            Math.round(
                              (new Date(job.completed_at).getTime() -
                                new Date(job.started_at).getTime()) /
                                1000
                            )
                          )
                        : job.status === 'running'
                        ? 'Running...'
                        : '-'}
                    </TableCell>
                    <TableCell>
                      {job.exit_code !== undefined && job.exit_code !== null ? (
                        <Badge
                          variant={job.exit_code === 0 ? 'success' : 'destructive'}
                        >
                          {job.exit_code}
                        </Badge>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/jobs/${job.id}`}>View</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {jobs.length} of {pagination.total} jobs
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              disabled={page === pagination.pages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function JobStatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    {
      variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';
      icon: React.ComponentType<{ className?: string }>;
    }
  > = {
    pending: { variant: 'warning', icon: Clock },
    queued: { variant: 'secondary', icon: Clock },
    running: { variant: 'success', icon: Loader2 },
    completed: { variant: 'default', icon: CheckCircle },
    failed: { variant: 'destructive', icon: AlertTriangle },
    cancelled: { variant: 'outline', icon: Square },
  };

  const { variant, icon: Icon } = config[status] || {
    variant: 'secondary',
    icon: Clock,
  };

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className={`h-3 w-3 ${status === 'running' ? 'animate-spin' : ''}`} />
      {status}
    </Badge>
  );
}

function JobsTableSkeleton() {
  return (
    <div className="p-4 space-y-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-6 w-12" />
          <Skeleton className="h-8 w-16 ml-auto" />
        </div>
      ))}
    </div>
  );
}
