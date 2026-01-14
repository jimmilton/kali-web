'use client';

import Link from 'next/link';
import {
  FolderKanban,
  Server,
  Bug,
  Terminal,
  ArrowRight,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  Key,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/layout/breadcrumbs';
import { useProjects } from '@/hooks/use-projects';
import { useJobs } from '@/hooks/use-jobs';
import { useAnalytics } from '@/hooks/use-analytics';
import { formatRelativeTime } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import {
  VulnerabilityChart,
  AssetChart,
  JobChart,
  ActivityTimeline,
} from '@/components/dashboard';

interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: {
    value: number;
    label: string;
  };
}

function StatCard({ title, value, description, icon: Icon, trend }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
        {trend && (
          <div className="mt-2 flex items-center gap-1 text-xs">
            <TrendingUp className="h-3 w-3 text-green-500" />
            <span className="text-green-500">+{trend.value}%</span>
            <span className="text-muted-foreground">{trend.label}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { projects, isLoading: projectsLoading } = useProjects();
  const { jobs, isLoading: jobsLoading } = useJobs({ autoRefresh: true, refreshInterval: 10000 });
  const { analytics, isLoading: analyticsLoading } = useAnalytics({ days: 30 });

  const activeProjects = projects.filter((p) => p.status === 'active').length;
  const runningJobs = jobs.filter((j) => j.status === 'running').length;
  const recentJobs = jobs.slice(0, 5);

  const isLoading = projectsLoading || analyticsLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your security testing activities"
      >
        <Button asChild>
          <Link href="/projects/new">
            New Project
          </Link>
        </Button>
      </PageHeader>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <>
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="mt-2 h-3 w-32" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : (
          <>
            <StatCard
              title="Active Projects"
              value={activeProjects}
              description={`${analytics?.stats.projects || projects.length} total projects`}
              icon={FolderKanban}
            />
            <StatCard
              title="Total Assets"
              value={analytics?.stats.assets || 0}
              description="Hosts, domains, URLs"
              icon={Server}
            />
            <StatCard
              title="Vulnerabilities"
              value={analytics?.stats.vulnerabilities || 0}
              description={`${analytics?.vulnerability_summary.critical || 0} critical, ${analytics?.vulnerability_summary.high || 0} high`}
              icon={Bug}
            />
            <StatCard
              title="Credentials"
              value={analytics?.stats.credentials || 0}
              description={`${runningJobs} jobs running`}
              icon={Key}
            />
          </>
        )}
      </div>

      {/* Charts Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {analyticsLoading ? (
          <>
            {[...Array(2)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-4 w-48" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-[250px] w-full" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : analytics ? (
          <>
            <VulnerabilityChart
              trends={analytics.vulnerability_trends}
              summary={analytics.vulnerability_summary}
            />
            <AssetChart
              byType={analytics.asset_by_type}
              total={analytics.stats.assets}
            />
          </>
        ) : null}
      </div>

      {/* Jobs and Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {analyticsLoading ? (
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-48" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[250px] w-full" />
            </CardContent>
          </Card>
        ) : analytics ? (
          <JobChart
            trends={analytics.job_trends}
            completed={analytics.stats.jobs_completed}
            running={analytics.stats.jobs_running}
            failed={analytics.stats.jobs_failed}
          />
        ) : null}

        {analyticsLoading ? (
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-48" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[300px] w-full" />
            </CardContent>
          </Card>
        ) : analytics ? (
          <ActivityTimeline vulnerabilities={analytics.top_vulnerabilities} />
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Projects */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Projects</CardTitle>
                <CardDescription>Your most recently updated projects</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/projects">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {projectsLoading ? (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded" />
                    <div className="flex-1">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="mt-1 h-3 w-48" />
                    </div>
                  </div>
                ))}
              </div>
            ) : projects.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <FolderKanban className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-2 text-sm text-muted-foreground">No projects yet</p>
                <Button className="mt-4" asChild>
                  <Link href="/projects/new">Create your first project</Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {projects.slice(0, 5).map((project) => (
                  <Link
                    key={project.id}
                    href={`/projects/${project.id}`}
                    className="flex items-center gap-4 rounded-lg p-2 transition-colors hover:bg-accent"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded bg-primary/10 text-primary">
                      <FolderKanban className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{project.name}</p>
                      <p className="text-sm text-muted-foreground truncate">
                        {project.description || 'No description'}
                      </p>
                    </div>
                    <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
                      {project.status}
                    </Badge>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Jobs</CardTitle>
                <CardDescription>Latest tool executions</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/jobs">
                  View all <ArrowRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {jobsLoading ? (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded" />
                    <div className="flex-1">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="mt-1 h-3 w-48" />
                    </div>
                  </div>
                ))}
              </div>
            ) : recentJobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Terminal className="h-12 w-12 text-muted-foreground/50" />
                <p className="mt-2 text-sm text-muted-foreground">No jobs yet</p>
                <Button className="mt-4" asChild>
                  <Link href="/tools">Run a tool</Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {recentJobs.map((job) => (
                  <Link
                    key={job.id}
                    href={`/jobs/${job.id}`}
                    className="flex items-center gap-4 rounded-lg p-2 transition-colors hover:bg-accent"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded bg-primary/10">
                      <JobStatusIcon status={job.status} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">{job.tool_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatRelativeTime(job.created_at)}
                      </p>
                    </div>
                    <JobStatusBadge status={job.status} />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function JobStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'running':
      return <Activity className="h-5 w-5 text-green-500 animate-pulse" />;
    case 'pending':
    case 'queued':
      return <Clock className="h-5 w-5 text-yellow-500" />;
    case 'completed':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'failed':
      return <AlertTriangle className="h-5 w-5 text-red-500" />;
    default:
      return <Terminal className="h-5 w-5 text-muted-foreground" />;
  }
}

function JobStatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
    running: 'success',
    pending: 'warning',
    queued: 'secondary',
    completed: 'default',
    failed: 'destructive',
    cancelled: 'outline',
  };

  return (
    <Badge variant={variants[status] || 'secondary'}>
      {status}
    </Badge>
  );
}
