'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Bug, Search, Filter, Plus, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
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

const severityColors: Record<string, string> = {
  critical: 'bg-critical text-white',
  high: 'bg-high text-white',
  medium: 'bg-medium text-white',
  low: 'bg-low text-white',
  info: 'bg-info text-white',
};

export default function ProjectVulnerabilitiesPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { project, isLoading } = useProject(projectId);
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');

  // Mock vulnerabilities for now - would come from API
  const vulnerabilities: Array<{
    id: string;
    title: string;
    severity: string;
    status: string;
    asset: string;
    cvss: number;
    created_at: string;
  }> = [];

  if (isLoading) {
    return <VulnsSkeleton />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vulnerabilities"
        description={`Security findings for ${project?.name || 'project'}`}
      >
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add Finding
        </Button>
      </PageHeader>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        {['critical', 'high', 'medium', 'low', 'info'].map((severity) => (
          <Card key={severity}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <span className="capitalize text-sm font-medium">{severity}</span>
                <Badge className={severityColors[severity]}>0</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="py-3">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search vulnerabilities..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {vulnerabilities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Bug className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold">No vulnerabilities found</h3>
              <p className="text-muted-foreground mt-1">
                Run a vulnerability scan to discover security issues
              </p>
              <Button className="mt-4" asChild>
                <Link href="/tools">Run Vulnerability Scan</Link>
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Asset</TableHead>
                  <TableHead>CVSS</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Found</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {vulnerabilities.map((vuln) => (
                  <TableRow key={vuln.id}>
                    <TableCell>
                      <Badge className={severityColors[vuln.severity]}>
                        {vuln.severity}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{vuln.title}</TableCell>
                    <TableCell className="font-mono text-sm">{vuln.asset}</TableCell>
                    <TableCell>{vuln.cvss}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{vuln.status}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(vuln.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function VulnsSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <div className="grid gap-4 md:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
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
