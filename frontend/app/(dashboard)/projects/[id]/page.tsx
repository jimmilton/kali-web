'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Server,
  Bug,
  Key,
  FileText,
  Terminal,
  Play,
  TrendingUp,
  AlertTriangle,
  Activity,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useProject } from '@/hooks/use-projects';
import { useJobs } from '@/hooks/use-jobs';
import { formatRelativeTime } from '@/lib/utils';

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;

  const { project, stats, isLoading } = useProject(projectId);
  const { jobs } = useJobs({ projectId });

  if (isLoading) {
    return <ProjectSkeleton />;
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h2 className="text-xl font-semibold">Project not found</h2>
        <p className="text-muted-foreground">The project you're looking for doesn't exist.</p>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    );
  }

  const recentJobs = jobs.slice(0, 5);

  return (
    <div className="space-y-6">
      <PageHeader
        title={project.name}
        description={project.description || 'No description'}
      >
        <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
          {project.status}
        </Badge>
        <Button asChild>
          <Link href="/tools">
            <Play className="mr-2 h-4 w-4" />
            Run Tool
          </Link>
        </Button>
      </PageHeader>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Assets"
          value={stats?.assets || 0}
          icon={Server}
          href={`/projects/${projectId}/assets`}
        />
        <StatCard
          title="Vulnerabilities"
          value={stats?.vulnerabilities ? Object.values(stats.vulnerabilities).reduce((a, b) => a + b, 0) : 0}
          icon={Bug}
          href={`/projects/${projectId}/vulnerabilities`}
          badge={stats?.vulnerabilities?.critical ? `${stats.vulnerabilities.critical} Critical` : undefined}
          badgeVariant="critical"
        />
        <StatCard
          title="Credentials"
          value="--"
          icon={Key}
          href={`/projects/${projectId}/credentials`}
        />
        <StatCard
          title="Reports"
          value="--"
          icon={FileText}
          href={`/projects/${projectId}/reports`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Vulnerability Summary */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Vulnerability Summary</CardTitle>
                <CardDescription>Findings by severity</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link href={`/projects/${projectId}/vulnerabilities`}>
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {stats?.vulnerabilities ? (
              <div className="space-y-3">
                <SeverityBar label="Critical" count={stats.vulnerabilities.critical} color="bg-critical" />
                <SeverityBar label="High" count={stats.vulnerabilities.high} color="bg-high" />
                <SeverityBar label="Medium" count={stats.vulnerabilities.medium} color="bg-medium" />
                <SeverityBar label="Low" count={stats.vulnerabilities.low} color="bg-low" />
                <SeverityBar label="Info" count={stats.vulnerabilities.info} color="bg-info" />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Bug className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-2 text-sm text-muted-foreground">No vulnerabilities yet</p>
                <Button className="mt-4" variant="outline" asChild>
                  <Link href="/tools">Run a vulnerability scan</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Scans</CardTitle>
                <CardDescription>Latest tool executions</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link href={`/projects/${projectId}/scans`}>
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {recentJobs.length > 0 ? (
              <div className="space-y-4">
                {recentJobs.map((job) => (
                  <Link
                    key={job.id}
                    href={`/jobs/${job.id}`}
                    className="flex items-center gap-4 rounded-lg p-2 transition-colors hover:bg-accent"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded bg-primary/10">
                      <Terminal className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">{job.tool_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatRelativeTime(job.created_at)}
                      </p>
                    </div>
                    <Badge variant={getStatusVariant(job.status)}>
                      {job.status}
                    </Badge>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Terminal className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-2 text-sm text-muted-foreground">No scans yet</p>
                <Button className="mt-4" asChild>
                  <Link href="/tools">
                    <Play className="mr-2 h-4 w-4" />
                    Run your first scan
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Scope */}
      {project.scope && (project.scope.domains?.length || project.scope.ips?.length) && (
        <Card>
          <CardHeader>
            <CardTitle>Project Scope</CardTitle>
            <CardDescription>Defined targets and boundaries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {project.scope.domains && project.scope.domains.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Domains</h4>
                  <div className="flex flex-wrap gap-1">
                    {project.scope.domains.map((domain, i) => (
                      <Badge key={i} variant="secondary">{domain}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {project.scope.ips && project.scope.ips.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">IPs/Networks</h4>
                  <div className="flex flex-wrap gap-1">
                    {project.scope.ips.map((ip, i) => (
                      <Badge key={i} variant="secondary">{ip}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {project.scope.exclude && project.scope.exclude.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Exclusions</h4>
                  <div className="flex flex-wrap gap-1">
                    {project.scope.exclude.map((ex, i) => (
                      <Badge key={i} variant="outline" className="border-destructive text-destructive">{ex}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  badge?: string;
  badgeVariant?: 'critical' | 'high' | 'medium' | 'low' | 'info';
}

function StatCard({ title, value, icon: Icon, href, badge, badgeVariant }: StatCardProps) {
  return (
    <Link href={href}>
      <Card className="card-hover">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-end justify-between">
            <div className="text-2xl font-bold">{value}</div>
            {badge && (
              <Badge variant={badgeVariant}>{badge}</Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

interface SeverityBarProps {
  label: string;
  count: number;
  color: string;
}

function SeverityBar({ label, count, color }: SeverityBarProps) {
  const maxWidth = 100;
  const width = Math.min(count * 10, maxWidth);

  return (
    <div className="flex items-center gap-4">
      <div className="w-16 text-sm font-medium">{label}</div>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-300`}
          style={{ width: `${width}%` }}
        />
      </div>
      <div className="w-8 text-sm text-right font-medium">{count}</div>
    </div>
  );
}

function getStatusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
    running: 'success',
    pending: 'warning',
    queued: 'secondary',
    completed: 'default',
    failed: 'destructive',
    cancelled: 'outline',
  };
  return variants[status] || 'secondary';
}

function ProjectSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-96" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
