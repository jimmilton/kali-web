'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Terminal,
  Play,
  Square,
  RotateCcw,
  Download,
  Clock,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Copy,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useToast } from '@/components/ui/use-toast';
import { useJob, useJobActions, useJobOutput as useJobOutputApi } from '@/hooks/use-jobs';
import { useJobOutput as useJobOutputSocket } from '@/hooks/use-socket';
import { formatDate, formatDuration, copyToClipboard, downloadFile } from '@/lib/utils';
import { TerminalOutput } from '@/components/terminal/terminal-output';

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const { toast } = useToast();

  const { job, isLoading } = useJob(jobId);
  const { outputs: apiOutputs } = useJobOutputApi(jobId);
  const { outputs: socketOutputs, status: liveStatus, sendInput, clearOutputs } = useJobOutputSocket(jobId);

  // Combine API outputs with socket outputs, preferring socket for newer entries
  const outputs = apiOutputs.length > 0 ? apiOutputs.map(o => ({
    content: o.content,
    output_type: o.output_type,
    job_id: jobId,
    timestamp: o.timestamp
  })) : socketOutputs;
  const { cancel, retry, isLoading: actionLoading } = useJobActions(jobId);

  const currentStatus = liveStatus?.status || job?.status || 'pending';
  const isRunning = currentStatus === 'running';
  const isFinished = ['completed', 'failed', 'cancelled'].includes(currentStatus);

  const handleCancel = async () => {
    await cancel();
    toast({ title: 'Job cancelled' });
  };

  const handleRetry = async () => {
    const newJob = await retry();
    if (newJob) {
      toast({ title: 'Job restarted' });
    }
  };

  const handleCopyOutput = () => {
    const text = outputs.map((o) => o.content).join('');
    copyToClipboard(text);
    toast({ title: 'Output copied to clipboard' });
  };

  const handleDownloadOutput = () => {
    const text = outputs.map((o) => o.content).join('');
    downloadFile(text, `job-${jobId}-output.txt`);
  };

  if (isLoading) {
    return <JobSkeleton />;
  }

  if (!job) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h2 className="text-xl font-semibold">Job not found</h2>
        <Button className="mt-4" asChild>
          <Link href="/jobs">Back to Jobs</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${job.tool_name} Job`}
        description={`Job ID: ${job.id}`}
      >
        <JobStatusBadge status={currentStatus} />
        <div className="flex gap-2">
          {isRunning && (
            <Button variant="destructive" onClick={handleCancel} disabled={actionLoading}>
              <Square className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          {isFinished && (
            <Button variant="outline" onClick={handleRetry} disabled={actionLoading}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
        </div>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Terminal Output */}
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4" />
                <CardTitle className="text-base">Output</CardTitle>
                {isRunning && (
                  <Loader2 className="h-4 w-4 animate-spin text-green-500" />
                )}
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" onClick={handleCopyOutput}>
                  <Copy className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={handleDownloadOutput}>
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
              <TerminalOutput
                outputs={outputs}
                onInput={isRunning ? sendInput : undefined}
              />
            </CardContent>
          </Card>
        </div>

        {/* Job Details */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Job Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <DetailRow label="Status">
                <JobStatusBadge status={currentStatus} />
              </DetailRow>
              <DetailRow label="Tool">{job.tool_name}</DetailRow>
              <DetailRow label="Created">{formatDate(job.created_at)}</DetailRow>
              {job.started_at && (
                <DetailRow label="Started">{formatDate(job.started_at)}</DetailRow>
              )}
              {job.completed_at && (
                <DetailRow label="Completed">{formatDate(job.completed_at)}</DetailRow>
              )}
              {job.started_at && job.completed_at && (
                <DetailRow label="Duration">
                  {formatDuration(
                    Math.round(
                      (new Date(job.completed_at).getTime() -
                        new Date(job.started_at).getTime()) /
                        1000
                    )
                  )}
                </DetailRow>
              )}
              {job.exit_code !== undefined && (
                <DetailRow label="Exit Code">
                  <Badge variant={job.exit_code === 0 ? 'success' : 'destructive'}>
                    {job.exit_code}
                  </Badge>
                </DetailRow>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Parameters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(job.parameters).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{key}</span>
                    <span className="font-mono text-xs truncate max-w-[150px]">
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {job.command && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Command</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg bg-muted p-3 font-mono text-xs break-all">
                  {job.command}
                </div>
              </CardContent>
            </Card>
          )}

          {job.error_message && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-base text-destructive">Error</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-destructive">{job.error_message}</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{children}</span>
    </div>
  );
}

function JobStatusBadge({ status }: { status: string }) {
  const config: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'; icon: React.ComponentType<{ className?: string }> }> = {
    pending: { variant: 'warning', icon: Clock },
    queued: { variant: 'secondary', icon: Clock },
    running: { variant: 'success', icon: Loader2 },
    completed: { variant: 'default', icon: CheckCircle },
    failed: { variant: 'destructive', icon: AlertTriangle },
    cancelled: { variant: 'outline', icon: Square },
  };

  const { variant, icon: Icon } = config[status] || { variant: 'secondary', icon: Clock };

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className={`h-3 w-3 ${status === 'running' ? 'animate-spin' : ''}`} />
      {status}
    </Badge>
  );
}

function JobSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-96" />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card className="h-[600px]">
            <CardHeader>
              <Skeleton className="h-5 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-full w-full" />
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-32" />
            </CardHeader>
            <CardContent className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
