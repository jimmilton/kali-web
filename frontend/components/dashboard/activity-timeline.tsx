'use client';

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import {
  Bug,
  Server,
  Terminal,
  AlertTriangle,
  CheckCircle,
  Shield,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TopVulnerability {
  id: string;
  title: string;
  severity: string;
  status: string;
  cvss_score: number | null;
  asset: string | null;
  created_at: string;
}

interface ActivityTimelineProps {
  vulnerabilities: TopVulnerability[];
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; icon: typeof Bug }> = {
  critical: { bg: 'bg-red-500/10', text: 'text-red-500', icon: AlertTriangle },
  high: { bg: 'bg-orange-500/10', text: 'text-orange-500', icon: Bug },
  medium: { bg: 'bg-yellow-500/10', text: 'text-yellow-500', icon: Shield },
  low: { bg: 'bg-green-500/10', text: 'text-green-500', icon: CheckCircle },
  info: { bg: 'bg-blue-500/10', text: 'text-blue-500', icon: Server },
};

export function ActivityTimeline({ vulnerabilities }: ActivityTimelineProps) {
  if (vulnerabilities.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Critical and high severity findings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Shield className="h-12 w-12 mb-2 opacity-50" />
            <p>No critical vulnerabilities found</p>
            <p className="text-sm">Run scans to discover security issues</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Critical and high severity findings</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          <div className="space-y-4">
            {vulnerabilities.map((vuln) => {
              const style = SEVERITY_STYLES[vuln.severity] || SEVERITY_STYLES.info;
              const Icon = style.icon;

              return (
                <Link
                  key={vuln.id}
                  href={`/vulnerabilities/${vuln.id}`}
                  className="flex items-start gap-4 rounded-lg p-3 transition-colors hover:bg-accent"
                >
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${style.bg}`}>
                    <Icon className={`h-5 w-5 ${style.text}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{vuln.title}</p>
                      <Badge
                        variant={
                          vuln.severity === 'critical' ? 'destructive' :
                          vuln.severity === 'high' ? 'destructive' :
                          'secondary'
                        }
                        className="shrink-0"
                      >
                        {vuln.severity}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      {vuln.asset && (
                        <span className="truncate">{vuln.asset}</span>
                      )}
                      {vuln.cvss_score && (
                        <span className="shrink-0">CVSS: {vuln.cvss_score}</span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(new Date(vuln.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
